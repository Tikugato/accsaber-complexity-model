import logging

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from complexity_model.beatmap import BeatmapError, load_difficulty
from complexity_model.model import NoteAccuracyModel
from complexity_model.patterns import swing_shares

app = FastAPI(title="AccSaber Complexity Model")
log = logging.getLogger("uvicorn.error")
model = NoteAccuracyModel()


@app.get("/health")
def health():
    return {"status": "ok", "model": model.name, "modelHash": model.fingerprint}


@app.post("/note-accuracies")
async def note_accuracies(
    zip: UploadFile = File(...),
    difficulty: str = Form(...),
    characteristic: str = Form("Standard"),
):
    zip_bytes = await zip.read()
    try:
        parsed = load_difficulty(zip_bytes, characteristic, difficulty)
    except BeatmapError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.exception("could not read the map for difficulty=%s characteristic=%s", difficulty, characteristic)
        raise HTTPException(status_code=500, detail=f"parse error: {exc}")

    prediction = model.predict(parsed)
    shares = swing_shares(parsed.notes)
    return {
        "model": model.name,
        "modelHash": model.fingerprint,
        "mapVersion": parsed.version,
        "njs": parsed.njs,
        "characteristic": parsed.characteristic,
        "difficulty": parsed.difficulty,
        "notes": prediction.notes,
        "predictedNotes": len(prediction.accuracies),
        "meanAccuracy": prediction.mean_accuracy,
        "noteAccuracies": prediction.accuracies,
        "noteTimes": prediction.times,
        "resetShare": shares.reset_share,
        "dotShare": shares.dot_share,
    }
