import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from complexity_model.beatmap import load_difficulty
from complexity_model.model import NoteAccuracyModel


def main(zip_path: str, difficulty: str, characteristic: str) -> int:
    parsed = load_difficulty(Path(zip_path).read_bytes(), characteristic, difficulty)
    model = NoteAccuracyModel()
    prediction = model.predict(parsed)
    print(json.dumps({
        "model": model.name,
        "modelHash": model.fingerprint,
        "mapVersion": parsed.version,
        "notes": prediction.notes,
        "predictedNotes": len(prediction.accuracies),
        "meanAccuracy": prediction.mean_accuracy,
        "noteAccuracies": prediction.accuracies,
        "noteTimes": prediction.times,
    }, indent=2))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: predict.py <map.zip> <difficulty> [characteristic]")
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Standard"))
