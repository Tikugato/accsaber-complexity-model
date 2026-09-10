import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from complexity_model.beatmap import BeatmapError, load_difficulty
from complexity_model.patterns import swing_shares


def main(ratings_csv: str, out_csv: str) -> int:
    cache = Path(__file__).resolve().parent.parent / ".cache" / "maps"
    rows = list(csv.DictReader(open(ratings_csv, encoding="utf-8")))
    with open(out_csv, "w", newline="", encoding="utf-8") as handle:
        out = csv.writer(handle)
        out.writerow(["accsaberId", "resetShare", "dotShare", "pairs"])
        done = 0
        for r in rows:
            zip_path = cache / f"{r['songHash']}.zip"
            if not zip_path.exists() or not r.get("blDifficultyName"):
                continue
            try:
                parsed = load_difficulty(zip_path.read_bytes(), r["blCharacteristic"] or "Standard", r["blDifficultyName"])
            except BeatmapError as exc:
                print("skip", r["songName"], exc, file=sys.stderr)
                continue
            shares = swing_shares(parsed.notes)
            out.writerow([r["accsaberId"], f"{shares.reset_share:.5f}", f"{shares.dot_share:.5f}", shares.pairs])
            done += 1
    print("done", done)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: reset_features.py <bl-ratings.csv> <out.csv>")
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
