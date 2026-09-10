import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort

from complexity_model.beatmap import ParsedDifficulty
from complexity_model.encoding import PREDICTION, encode_map, segments

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_NAME = os.environ.get("COMPLEXITY_MODEL_FILE", "note-acc-beatleader.onnx")
INPUT_NAME = "input_1"
OUTPUT_NAME = "time_distributed_2"


@dataclass(frozen=True)
class NotePrediction:
    accuracies: list[float]
    times: list[float]
    notes: int

    @property
    def mean_accuracy(self) -> float:
        return float(np.mean(self.accuracies)) if self.accuracies else 0.0


class NoteAccuracyModel:
    def __init__(self, path: Path | None = None):
        self.path = path or MODEL_DIR / MODEL_NAME
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self._session = ort.InferenceSession(str(self.path), options, providers=["CPUExecutionProvider"])
        self.fingerprint = hashlib.sha256(self.path.read_bytes()).hexdigest()[:16]

    @property
    def name(self) -> str:
        return self.path.stem

    def predict(self, difficulty: ParsedDifficulty) -> NotePrediction:
        encoded, times = encode_map(difficulty.notes)
        batches = segments(encoded)
        if batches.shape[0] == 0:
            return NotePrediction([], [], encoded.shape[0])
        output = self._session.run([OUTPUT_NAME], {INPUT_NAME: batches})[0]
        flat = np.asarray(output, dtype=np.float32).reshape(-1, PREDICTION)
        accuracies = [float(max(0.0, value)) for value in flat.reshape(-1)]
        return NotePrediction(accuracies, times[:len(accuracies)], encoded.shape[0])
