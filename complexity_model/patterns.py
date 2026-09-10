from dataclasses import dataclass

from complexity_model.beatmap import Note

DOT = 8
VECTORS = {0: (0, 1), 1: (0, -1), 2: (-1, 0), 3: (1, 0), 4: (-1, 1), 5: (1, 1), 6: (-1, -1), 7: (1, -1)}
SAME_TIME = 1e-3


@dataclass(frozen=True)
class SwingShares:
    reset_share: float
    dot_share: float
    pairs: int


def swing_shares(notes: list[Note]) -> SwingShares:
    by_color: dict[int, list[Note]] = {0: [], 1: []}
    for note in notes:
        if note.color in by_color:
            by_color[note.color].append(note)
    total = sum(len(v) for v in by_color.values())
    if total == 0:
        return SwingShares(0.0, 0.0, 0)
    dots = sum(1 for v in by_color.values() for n in v if n.direction == DOT)
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
    return SwingShares(resets / pairs if pairs else 0.0, dots / total, pairs)


def _dot(first: int, second: int) -> int:
    a, b = VECTORS[first], VECTORS[second]
    return a[0] * b[0] + a[1] * b[1]
