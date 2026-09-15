from dataclasses import dataclass

from complexity_model.beatmap import Note

DOT = 8
VECTORS = {0: (0, 1), 1: (0, -1), 2: (-1, 0), 3: (1, 0), 4: (-1, 1), 5: (1, 1), 6: (-1, -1), 7: (1, -1)}
SAME_TIME = 1e-3
UPWARD = {0, 4, 5}
DOWNWARD = {1, 6, 7}
UP_DIAGONAL = {4, 5}
DOWN_DIAGONAL = {6, 7}
BOTTOM_ROW = 0
MIDDLE_ROW = 1
TOP_ROW = 2


@dataclass(frozen=True)
class SwingShares:
    reset_share: float
    dot_share: float
    bottom_up_share: float
    top_down_share: float
    mid_diag_double_share: float
    pairs: int


def swing_shares(notes: list[Note]) -> SwingShares:
    by_color: dict[int, list[Note]] = {0: [], 1: []}
    for note in notes:
        if note.color in by_color:
            by_color[note.color].append(note)
    total = sum(len(v) for v in by_color.values())
    if total == 0:
        return SwingShares(0.0, 0.0, 0.0, 0.0, 0.0, 0)
    dots = sum(1 for v in by_color.values() for n in v if n.direction == DOT)
    bottom_ups = sum(
        1 for v in by_color.values() for n in v if n.y == BOTTOM_ROW and n.direction in UPWARD
    )
    top_downs = sum(1 for v in by_color.values() for n in v if n.y == TOP_ROW and n.direction in DOWNWARD)
    pairs = 0
    resets = 0
    for hand in by_color.values():
        hand.sort(key=lambda n: n.seconds)
        for a, b in zip(hand, hand[1:]):
            if b.seconds - a.seconds < SAME_TIME:
                continue
            pairs += 1
            if a.direction == DOT or b.direction == DOT or _dot(a.direction, b.direction) > 0:
                resets += 1
    return SwingShares(
        resets / pairs if pairs else 0.0, dots / total, bottom_ups / total, top_downs / total,
        _mid_diag_doubles(by_color) / total, pairs
    )


def _mid_diag_doubles(by_color: dict[int, list[Note]]) -> int:
    reds = sorted(by_color[0], key=lambda n: n.seconds)
    blues = sorted(by_color[1], key=lambda n: n.seconds)
    count = 0
    j = 0
    for red in reds:
        while j < len(blues) and blues[j].seconds < red.seconds - SAME_TIME:
            j += 1
        k = j
        while k < len(blues) and blues[k].seconds <= red.seconds + SAME_TIME:
            blue = blues[k]
            if red.y == MIDDLE_ROW and blue.y == MIDDLE_ROW and _opposite_diagonals(red.direction, blue.direction):
                count += 2
            k += 1
    return count


def _opposite_diagonals(first: int, second: int) -> bool:
    return (first in UP_DIAGONAL and second in DOWN_DIAGONAL) or (first in DOWN_DIAGONAL and second in UP_DIAGONAL)


def _dot(first: int, second: int) -> int:
    a, b = VECTORS[first], VECTORS[second]
    return a[0] * b[0] + a[1] * b[1]
