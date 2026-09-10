import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from complexity_model.beatmap import BeatmapError, load_difficulty
from complexity_model.model import NoteAccuracyModel

DIFFICULTY_BY_NUMBER = {"1": "Easy", "3": "Normal", "5": "Hard", "7": "Expert", "9": "ExpertPlus"}
STEEPEST_MEAN_SLOPE = 18.052
STEEPEST_WORST_SLOPE = 4.473
WORST_SHARE = 0.05
RATING_TOLERANCE = 0.02


def linearised(accuracy: float) -> float:
    return -np.log10(1.0 - min(accuracy, 0.9999))


def complexity_bound(ours: np.ndarray, theirs: np.ndarray) -> float:
    if ours.size == 0:
        return 0.0
    worst_count = max(1, int(round(ours.size * WORST_SHARE)))
    mean_gap = abs(linearised(float(ours.mean())) - linearised(float(theirs.mean())))
    worst_gap = abs(linearised(float(np.sort(ours)[:worst_count].mean()))
                    - linearised(float(np.sort(theirs)[:worst_count].mean())))
    return STEEPEST_MEAN_SLOPE * mean_gap + STEEPEST_WORST_SLOPE * worst_gap


def fetch_zip(song_hash: str, cache: Path) -> bytes | None:
    target = cache / f"{song_hash}.zip"
    if target.exists():
        return target.read_bytes()
    request = urllib.request.Request(f"https://cdn.beatsaver.com/{song_hash}.zip",
                                     headers={"User-Agent": "accsaber-complexity-model validation"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
    except Exception as exc:
        print(f"{song_hash}: download failed ({exc})")
        return None
    target.write_bytes(data)
    time.sleep(0.5)
    return data


def main(stage_dir: str, limit: int) -> int:
    cache = Path(__file__).resolve().parent.parent / ".cache" / "maps"
    cache.mkdir(parents=True, exist_ok=True)
    model = NoteAccuracyModel()
    files = sorted(Path(stage_dir).glob("*.json"))[:limit]
    compared = 0
    worst = 0.0
    worst_rating = 0.0
    mismatched = []
    tolerated = []
    for file in files:
        song_hash, characteristic, number = file.stem.split("_")
        payload = json.loads(file.read_text(encoding="utf-8"))
        data = payload.get("data") or {}
        notes = (data.get("notes") or {}).get("rows")
        if not notes:
            continue
        zip_bytes = fetch_zip(song_hash, cache)
        if zip_bytes is None:
            continue
        try:
            parsed = load_difficulty(zip_bytes, characteristic, DIFFICULTY_BY_NUMBER[number])
        except BeatmapError as exc:
            mismatched.append((file.stem, f"parse: {exc}"))
            continue
        prediction = model.predict(parsed)
        theirs = np.asarray([row[0] for row in notes], dtype=np.float64)
        ours = np.asarray(prediction.accuracies, dtype=np.float64)
        if theirs.shape != ours.shape:
            mismatched.append((file.stem, f"count {ours.shape[0]} vs {theirs.shape[0]}"))
            continue
        gap = float(np.max(np.abs(theirs - ours))) if theirs.size else 0.0
        their_times = np.asarray([row[1] for row in notes], dtype=np.float64)
        time_gap = float(np.max(np.abs(their_times - np.asarray(prediction.times)))) if theirs.size else 0.0
        rating_gap = complexity_bound(ours, theirs)
        worst = max(worst, gap)
        worst_rating = max(worst_rating, rating_gap)
        compared += 1
        if rating_gap > RATING_TOLERANCE:
            mismatched.append((file.stem, f"complexity bound {rating_gap:.4f}, max acc gap {gap:.6f}, max time gap {time_gap:.4f}"))
        elif gap > 1e-4 or time_gap > 1e-3:
            tolerated.append((file.stem, f"max acc gap {gap:.6f}, max time gap {time_gap:.4f}, complexity bound {rating_gap:.4f}"))
        print(f"{file.stem}: {ours.shape[0]} notes, max acc gap {gap:.2e}, complexity bound {rating_gap:.4f}, "
              f"mean ours {ours.mean():.6f} theirs {theirs.mean():.6f}")
    print(f"\ncompared {compared} maps, worst per-note gap {worst:.2e}, worst complexity bound {worst_rating:.4f}, "
          f"{len(tolerated)} tolerated differences, {len(mismatched)} mismatches")
    for stem, reason in tolerated:
        print(f"  tolerated {stem}: {reason}")
    for stem, reason in mismatched:
        print(f"  {stem}: {reason}")
    return 1 if mismatched else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10 ** 9))
