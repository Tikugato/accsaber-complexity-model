from dataclasses import dataclass


@dataclass(frozen=True)
class BpmChange:
    beat: float
    bpm: float


class Timescale:
    def __init__(self, bpm: float, changes: list[BpmChange]):
        self._bpm = float(bpm)
        ordered = sorted(changes, key=lambda c: c.beat)
        self._scale = [(c.beat, self._bpm / c.bpm) for c in ordered]

    def to_seconds(self, beat: float) -> float:
        remaining = float(beat)
        scaled = 0.0
        for time, scale in reversed(self._scale):
            if remaining > time:
                scaled += (remaining - time) * scale
                remaining = time
        return (remaining + scaled) / self._bpm * 60.0
