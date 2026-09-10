import numpy as np

from complexity_model.beatmap import Note

PRE_SEGMENT = 12
POST_SEGMENT = 12
PREDICTION = 8
NOTE_SIZE = 49
SEGMENT = PRE_SEGMENT + PREDICTION + POST_SEGMENT

_DIRECTION_TO_ANGLE = {0: 180, 1: 0, 2: 90, 3: 270, 4: 135, 5: 225, 6: 45, 7: 315}
_ANGLE_TO_DIRECTION = {angle: direction for direction, angle in _DIRECTION_TO_ANGLE.items()}


def note_direction(direction: int, angle_offset: float) -> int:
    if direction == 8:
        return 8
    angle = (_DIRECTION_TO_ANGLE[direction] - int(round(angle_offset / 45.0)) * 45) % 360
    return _ANGLE_TO_DIRECTION[angle]


def ordered_notes(notes: list[Note]) -> list[tuple[float, str, float]]:
    rows = []
    for note in notes:
        if not (0 <= note.x < 1000 and 0 <= note.y < 1000):
            continue
        key = f"{note.x}{note.y}{note_direction(note.direction, note.angle_offset)}{note.color}"
        rows.append((note.seconds, key, note.njs))
    rows.sort(key=lambda row: (row[0], row[1]))
    return rows


def encode_note(delta: float, delta_other: float, digits: list[int], njs: float) -> np.ndarray:
    delta_long = max(0.0, 2.0 - delta) / 2.0
    delta_other_long = max(0.0, 2.0 - delta_other) / 2.0
    delta_short = max(0.0, 0.5 - delta) * 2.0
    delta_other_short = max(0.0, 0.5 - delta_other) * 2.0

    col = min(max(digits[0], 0), 3)
    row = min(max(digits[1], 0), 2)
    direction = digits[2]
    color = digits[-1]

    row_col = np.zeros(12)
    row_col[col * 3 + row] = 1.0
    direction_vector = np.zeros(10)
    direction_vector[direction] = 1.0
    empty_row_col = np.zeros(12)
    empty_direction = np.zeros(10)

    if color == 0:
        parts = [row_col, direction_vector, empty_row_col, empty_direction,
                 [delta_short, delta_long, delta_other_short, delta_other_long]]
    else:
        parts = [empty_row_col, empty_direction, row_col, direction_vector,
                 [delta_other_short, delta_other_long, delta_short, delta_long]]
    parts.append([njs / 30.0])
    return np.concatenate([np.asarray(p, dtype=np.float64) for p in parts])


def encode_map(notes: list[Note]) -> tuple[np.ndarray, list[float]]:
    rows = ordered_notes(notes)
    encoded = []
    times = []
    previous = {0: 0.0, 1: 0.0}
    for seconds, key, njs in rows:
        digits = [ord(c) - ord("0") for c in key]
        color = digits[-1]
        if color not in (0, 1):
            continue
        other = 1 - color
        delta = seconds - previous[color]
        delta_other = seconds - previous[other]
        previous[color] = seconds
        encoded.append(encode_note(delta, delta_other, digits, njs))
        times.append(seconds)
    if not encoded:
        return np.zeros((0, NOTE_SIZE)), []
    return np.vstack(encoded), times


def segments(encoded: np.ndarray) -> np.ndarray:
    count = encoded.shape[0]
    if count < PREDICTION:
        return np.zeros((0, SEGMENT, NOTE_SIZE), dtype=np.float32)
    out = []
    for start in range(0, count - PREDICTION + 1, PREDICTION):
        pre = encoded[max(0, start - PRE_SEGMENT):start]
        if pre.shape[0] < PRE_SEGMENT:
            pre = np.vstack([np.zeros((PRE_SEGMENT - pre.shape[0], NOTE_SIZE)), pre])
        middle = encoded[start:start + PREDICTION]
        post = encoded[start + PREDICTION:start + PREDICTION + POST_SEGMENT]
        if post.shape[0] < POST_SEGMENT:
            post = np.vstack([post, np.zeros((POST_SEGMENT - post.shape[0], NOTE_SIZE))])
        out.append(np.vstack([pre, middle, post]))
    return np.asarray(out, dtype=np.float32)
