# AccSaber Complexity Model

The service behind AccSaber's complexity script. It takes a Beat Saber map, runs a per-note accuracy model over it and hands back one predicted accuracy per note. The backend turns that list into a complexity. This repo owns the model and nothing else.

The model in `models/` is BeatLeader's shipped network, `model_sleep_bl.onnx` from their MIT licensed [RatingAPI](https://github.com/BeatLeader/RatingAPI), pinned here as `note-acc-beatleader.onnx` with the licence next to it. The map parsing and the note encoding are a port of what feeds that network on their side, and `scripts/validate_against_stage.py` checks the port against their live output note for note. Pinning the weights is the point. Their service gets retrained without notice, and a number that moves under a map after it is ranked is the problem this replaces.

## Running it

```
uv sync
uv run uvicorn server:app --port 8000
```

Or build the image, which is what staging and prod run:

```
docker build -t accsaber-complexity-model .
docker run -p 8000:8000 accsaber-complexity-model
```

`GET /health` answers with the model name and a short hash of the model file. `POST /note-accuracies` takes a multipart body with the map zip as `zip`, the difficulty as `difficulty`, either a name from `Easy` to `ExpertPlus` or one of the numbers 1 to 9, and the characteristic as `characteristic`, `Standard` unless you say otherwise. You get back the per-note accuracies in map order, their times in seconds, the note count, the map's base NJS, the model name and the same hash, plus two swing shares the backend prices reset maps with: `resetShare`, the share of consecutive same colour notes where the second swing repeats the direction of the first, a dot note counting as a repeat, and `dotShare`, the share of notes that are dots. The backend stores all of it next to every number it produces.

To try one map without the server:

```
uv run python scripts/predict.py path/to/map.zip ExpertPlus
```

## What is in here

| File | What it does |
|---|---|
| `server.py` | The FastAPI app. Two routes, `/health` and `/note-accuracies`, and the error handling around a bad zip or a difficulty the map does not have. |
| `complexity_model/beatmap.py` | Opens the zip, reads `Info.dat`, finds the difficulty file and turns it into a list of notes with a time in seconds, grid position, colour, cut direction, angle offset and the NJS in force at that note. Handles v2, v3 and v4 maps. |
| `complexity_model/timescale.py` | Beats to seconds with BPM changes, the same way the BeatLeader parser does it. |
| `complexity_model/vnjs.py` | Variable NJS. Interpolates between NJS events with the game's easing curves, and a note gets the NJS it spawns with. |
| `complexity_model/encoding.py` | Turns each note into the 49 numbers the network reads, orders the notes the way BeatLeader orders them, and cuts the map into the 32-note windows the network predicts from. |
| `complexity_model/patterns.py` | Counts the swing shares. The network prices every note as a real swing, so a map of downs and dots looks like any other slow map to it. The reset share is what tells the two apart. |
| `complexity_model/model.py` | Loads the ONNX file with onnxruntime, runs the windows through it and lines the predictions back up with the notes. Also computes the model hash `/health` reports. |
| `models/` | The pinned weights and their licence. `COMPLEXITY_MODEL_FILE` picks which file in here the service loads. |
| `scripts/predict.py` | Runs one local map through the model and prints the result as JSON. |
| `scripts/reset_features.py` | Writes the swing shares of every cached ranked map to a CSV for fitting the true acc line. |
| `scripts/validate_against_stage.py` | Downloads every map in a folder of cached BeatLeader stage responses, runs it through this code and compares each predicted note against theirs. |
| `tests/` | Unit tests for the encoding, the windowing, the timescale, the NJS interpolation and the swing shares. |
| `training/` | Reserved for our own model. Empty apart from the note on what the service expects back. |
| `Dockerfile` | The image staging and prod run, built with uv on `python:3.12-slim`. |
| `.github/workflows/build-image.yml` | Tests, builds and publishes the image, then redeploys the backend stack that uses it. |

## What the model sees

Every colour note becomes 49 numbers: its column and row and cut direction, one-hot and split by colour, the time since the previous note of each colour on two scales, and NJS over 30. The network reads 32 notes at a time, 12 before, 8 to predict and 12 after, and predicts the 8 in the middle. The last few notes of a map that do not fill a block of 8 get no prediction. Bombs, walls, arcs and chain links are invisible to it, and chain heads count as notes. Variable NJS and BPM changes are applied the same way the BeatLeader parser applies them.

## Checking the port

```
uv run --group dev pytest
uv run python scripts/validate_against_stage.py <folder of cached stage responses> [limit]
```

The second one downloads each map from BeatSaver into `.cache/maps`, runs it through the service code and compares every predicted note against what BeatLeader's stage service answered for the same map. Most maps match to a few millionths. A handful differ by up to a few hundredths on a few notes, because BeatLeader's parser does its beat to second maths in single precision and its live service applies old style v2 BPM change entries that its published source ignores. Those are reported as tolerated, and the script only fails a map when the difference would move the complexity by more than 0.02, worked out with the steepest category slopes.

## How it ships

Push to `develop` and the workflow runs the tests, builds the image as `ghcr.io/tikugato/accsaber-complexity-model:develop` and asks Coolify to redeploy the staging stack. Push to `main` and the same happens with the `latest` tag and the prod stack. The stack pulls the new image, and the backend notices on its own: it checks `/health` every five minutes, and when the model hash differs from the one behind its stored estimates it reruns the complexity script over every ranked, qualified and queued map. Nothing on a map changes by itself. The new numbers land in the calibration panel and applying them stays a staff decision.

The workflow needs the same secrets the backend uses: `COOLIFY_URL`, `COOLIFY_TOKEN`, `COOLIFY_STAGING_UUID` and `COOLIFY_PROD_UUID`.

## Training

`training/` is where our own model goes once there is one. The service loads whatever `COMPLEXITY_MODEL_FILE` points at inside `models/`, and the only contract is the network's shape, `input_1` of `[batch, 32, 49]` in and `time_distributed_2` of `[batch, 8, 1]` out, both float32. Anything that keeps that shape drops in without touching the rest, and the encoding in `complexity_model/encoding.py` is there to reuse for the training side too.
