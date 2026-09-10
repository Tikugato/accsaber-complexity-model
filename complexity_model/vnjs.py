import math
from dataclasses import dataclass


@dataclass(frozen=True)
class NjsEvent:
    seconds: float
    delta: float
    easing: int


_C1 = 1.70158
_C2 = _C1 * 1.525
_C3 = _C1 + 1.0
_C4 = (2.0 * math.pi) / 3.0
_C5 = (2.0 * math.pi) / 4.5
_N1 = 7.5625
_D1 = 2.75


def _bounce_out(x: float) -> float:
    if x < 1 / _D1:
        return _N1 * x * x
    if x < 2 / _D1:
        x -= 1.5 / _D1
        return _N1 * x * x + 0.75
    if x < 2.5 / _D1:
        x -= 2.25 / _D1
        return _N1 * x * x + 0.9375
    x -= 2.625 / _D1
    return _N1 * x * x + 0.984375


def _beat_saber_in_out_back(t: float) -> float:
    if t < 0.517:
        return 5.014 * t * t * t
    a = (1.665 * (t - 0.4) - 1.0) ** 3
    b = (1.665 * (t - 0.4) - 1.0) ** 2
    return 1.0 + 2.70158 * a + 1.70158 * b


def _beat_saber_in_out_elastic(t: float) -> float:
    if t < 0.3:
        return 37.037 * t * t * t
    return math.pow(2.0, -10.0 * (t - 0.2)) * math.sin(t * 10.0 * 2.0943952) + 1.0


def _beat_saber_in_out_bounce(t: float) -> float:
    if t < 0.36363637:
        return 20.796 * t * t * t
    if t < 0.72727275:
        t -= 0.54545456
        return 7.5625 * t * t + 0.75
    if t < 0.90909094:
        t -= 0.8181818
        return 7.5625 * t * t + 0.9375
    t -= 0.95454544
    return 7.5625 * t * t + 0.984375


_EASINGS = {
    0: lambda x: x,
    1: lambda x: x * x,
    2: lambda x: 1 - (1 - x) * (1 - x),
    3: lambda x: 2 * x * x if x < 0.5 else 1 - ((-2 * x + 2) ** 2) / 2,
    19: lambda x: 1 - math.sqrt(1 - x ** 2),
    20: lambda x: math.sqrt(1 - (x - 1) ** 2),
    21: lambda x: (1 - math.sqrt(1 - (2 * x) ** 2)) / 2 if x < 0.5 else (math.sqrt(1 - (-2 * x + 2) ** 2) + 1) / 2,
    22: lambda x: _C3 * x * x * x - _C1 * x * x,
    23: lambda x: 1 + _C3 * (x - 1) ** 3 + _C1 * (x - 1) ** 2,
    24: lambda x: ((2 * x) ** 2 * ((_C2 + 1) * 2 * x - _C2)) / 2 if x < 0.5
    else ((2 * x - 2) ** 2 * ((_C2 + 1) * (x * 2 - 2) + _C2) + 2) / 2,
    25: lambda x: 0 if x == 0 else 1 if x == 1 else -math.pow(2, 10 * x - 10) * math.sin((x * 10 - 10.75) * _C4),
    26: lambda x: 0 if x == 0 else 1 if x == 1 else math.pow(2, -10 * x) * math.sin((x * 10 - 0.75) * _C4) + 1,
    27: lambda x: 0 if x == 0 else 1 if x == 1
    else -(math.pow(2, 20 * x - 10) * math.sin((20 * x - 11.125) * _C5)) / 2 if x < 0.5
    else (math.pow(2, -20 * x + 10) * math.sin((20 * x - 11.125) * _C5)) / 2 + 1,
    28: lambda x: 1 - _bounce_out(1 - x),
    29: _bounce_out,
    30: lambda x: (1 - _bounce_out(1 - 2 * x)) / 2 if x < 0.5 else (1 + _bounce_out(2 * x - 1)) / 2,
    100: _beat_saber_in_out_back,
    101: _beat_saber_in_out_elastic,
    102: _beat_saber_in_out_bounce,
}


def ease(t: float, easing: int) -> float:
    function = _EASINGS.get(easing)
    if function is None:
        return 1.0 if t >= 1.0 else 0.0
    return function(t)


class VariableNjs:
    def __init__(self, base_njs: float, events: list[NjsEvent]):
        self._base = float(base_njs)
        self._events = sorted(events, key=lambda e: e.seconds)

    def at(self, seconds: float) -> float:
        last = None
        following = None
        for event in self._events:
            if event.seconds <= seconds:
                last = event
            elif following is None:
                following = event
        if last is None:
            return self._base
        if following is None or following.easing == -1:
            return self._base + last.delta
        t = (seconds - last.seconds) / (following.seconds - last.seconds)
        t = ease(t, following.easing)
        return self._base + last.delta + t * (following.delta - last.delta)
