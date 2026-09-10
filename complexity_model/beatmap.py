import io
import json
import zipfile
from dataclasses import dataclass

import numpy as np

from complexity_model.timescale import BpmChange, Timescale
from complexity_model.vnjs import NjsEvent, VariableNjs

DIFFICULTY_NAMES = {
    "easy": "Easy",
    "normal": "Normal",
    "hard": "Hard",
    "expert": "Expert",
    "expertplus": "ExpertPlus",
    "1": "Easy",
    "3": "Normal",
    "5": "Hard",
    "7": "Expert",
    "9": "ExpertPlus",
}


class BeatmapError(ValueError):
    pass


@dataclass(frozen=True)
class Note:
    seconds: float
    x: int
    y: int
    color: int
    direction: int
    angle_offset: int
    njs: float


@dataclass(frozen=True)
class ParsedDifficulty:
    characteristic: str
    difficulty: str
    version: str
    bpm: float
    njs: float
    notes: list[Note]


def normalise_difficulty(value: str) -> str:
    key = str(value).replace("_", "").replace(" ", "").replace("+", "plus").lower()
    if key not in DIFFICULTY_NAMES:
        raise BeatmapError(f"unknown difficulty '{value}'")
    return DIFFICULTY_NAMES[key]


def load_difficulty(zip_bytes: bytes, characteristic: str, difficulty: str) -> ParsedDifficulty:
    try:
        archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise BeatmapError("not a valid zip") from exc
    files = {name.split("/")[-1].lower(): name for name in archive.namelist()}
    info_name = files.get("info.dat")
    if info_name is None:
        raise BeatmapError("Info.dat not found")
    info = _read_json(archive, info_name)
    wanted = normalise_difficulty(difficulty)
    if "difficultyBeatmaps" in info and "audio" in info:
        return _load_v4(archive, files, info, characteristic, wanted)
    return _load_v2_info(archive, files, info, characteristic, wanted)


def _read_json(archive: zipfile.ZipFile, name: str) -> dict:
    with archive.open(name) as handle:
        raw = handle.read()
    return json.loads(raw.decode("utf-8-sig"))


def _load_v2_info(archive, files, info, characteristic, wanted) -> ParsedDifficulty:
    bpm = float(info["_beatsPerMinute"])
    for beatmap_set in info.get("_difficultyBeatmapSets", []):
        if beatmap_set.get("_beatmapCharacteristicName", "").lower() != characteristic.lower():
            continue
        for beatmap in beatmap_set.get("_difficultyBeatmaps", []):
            if beatmap.get("_difficulty") != wanted:
                continue
            filename = beatmap["_beatmapFilename"]
            data = _read_json(archive, files.get(filename.lower(), filename))
            njs = float(beatmap.get("_noteJumpMovementSpeed", 0.0))
            if "_notes" in data and "colorBoostBeatmapEvents" not in data:
                return _from_v2(data, characteristic, wanted, bpm, njs)
            return _from_v3(data, characteristic, wanted, bpm, njs)
    raise BeatmapError(f"{characteristic} {wanted} not in this map")


def _load_v4(archive, files, info, characteristic, wanted) -> ParsedDifficulty:
    bpm = float(info["audio"]["bpm"])
    audio_name = info["audio"].get("audioDataFilename")
    audio = _read_json(archive, files[audio_name.lower()]) if audio_name and audio_name.lower() in files else None
    for beatmap in info.get("difficultyBeatmaps", []):
        if beatmap.get("characteristic", "").lower() != characteristic.lower():
            continue
        if beatmap.get("difficulty") != wanted:
            continue
        filename = beatmap["beatmapDataFilename"]
        data = _read_json(archive, files.get(filename.lower(), filename))
        njs = float(beatmap.get("noteJumpMovementSpeed", 0.0))
        return _from_v4(data, audio, characteristic, wanted, bpm, njs)
    raise BeatmapError(f"{characteristic} {wanted} not in this map")


def _from_v2(data, characteristic, wanted, bpm, njs) -> ParsedDifficulty:
    raw = []
    for note in data.get("_notes", []):
        if note.get("_type") not in (0, 1):
            continue
        raw.append((float(note.get("_time", 0.0)), int(note.get("_lineIndex", 0)), int(note.get("_lineLayer", 0)),
                    int(note["_type"]), int(note.get("_cutDirection", 0)), 0))
    return _finish(raw, [], [], characteristic, wanted, "2", bpm, njs)


def _from_v3(data, characteristic, wanted, bpm, njs) -> ParsedDifficulty:
    raw = [(float(n.get("b", 0.0)), int(n.get("x", 0)), int(n.get("y", 0)), int(n.get("c", 0)), int(n.get("d", 0)),
            int(n.get("a", 0))) for n in data.get("colorNotes", [])]
    bpm_changes = [BpmChange(float(e.get("b", 0.0)), float(e.get("m", 0.0))) for e in data.get("bpmEvents", [])
                   if float(e.get("m", 0.0)) > 0]
    njs_events = [(float(e["b"]), float(e.get("d", 0.0)), int(e.get("p", 0)), int(e.get("e", -1)))
                  for e in data.get("njsEvents", [])]
    return _finish(raw, bpm_changes, njs_events, characteristic, wanted, "3", bpm, njs)


def _from_v4(data, audio, characteristic, wanted, bpm, njs) -> ParsedDifficulty:
    note_data = data.get("colorNotesData", [])
    raw = []
    for note in data.get("colorNotes", []):
        index = int(note.get("i", 0))
        fields = note_data[index] if index < len(note_data) else {}
        raw.append((float(note.get("b", 0.0)), int(fields.get("x", 0)), int(fields.get("y", 0)),
                    int(fields.get("c", 0)), int(fields.get("d", 0)), int(fields.get("a", 0))))
    bpm_changes = []
    if audio and audio.get("bpmData"):
        frequency = float(audio["songFrequency"])
        for region in audio["bpmData"]:
            samples = float(region["ei"] - region["si"])
            region_bpm = ((float(region["eb"]) - float(region["sb"])) / (samples / frequency)) * 60.0
            bpm_changes.append(BpmChange(float(region["sb"]), region_bpm))
    event_data = data.get("njsEventData", [])
    njs_events = []
    for event in data.get("njsEvents", []):
        index = int(event.get("i", 0))
        fields = event_data[index] if index < len(event_data) else {}
        njs_events.append((float(event.get("b", 0.0)), float(fields.get("d", 0.0)), int(fields.get("p", 0)),
                           int(fields.get("e", -1))))
    return _finish(raw, bpm_changes, njs_events, characteristic, wanted, "4", bpm, njs)


def _finish(raw, bpm_changes, njs_events, characteristic, wanted, version, bpm, njs) -> ParsedDifficulty:
    timescale = Timescale(bpm, bpm_changes)
    resolved = []
    previous_delta = None
    for beat, delta, use_previous, easing in njs_events:
        if use_previous == 1 and previous_delta is not None:
            delta = previous_delta
        resolved.append(NjsEvent(float(np.float32(timescale.to_seconds(beat))), delta, easing))
        previous_delta = delta
    variable = VariableNjs(njs, resolved)
    notes = []
    for beat, x, y, color, direction, angle in raw:
        seconds = float(np.float32(timescale.to_seconds(beat)))
        notes.append(Note(seconds, x, y, color, direction, angle, float(np.float32(variable.at(seconds)))))
    return ParsedDifficulty(characteristic, wanted, version, bpm, njs, notes)
