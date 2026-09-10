import numpy as np

from complexity_model.beatmap import Note
from complexity_model.encoding import NOTE_SIZE, encode_map, note_direction, ordered_notes, segments
from complexity_model.timescale import BpmChange, Timescale
from complexity_model.vnjs import NjsEvent, VariableNjs


def note(seconds, x=1, y=0, color=0, direction=1, angle=0, njs=10.0):
    return Note(seconds, x, y, color, direction, angle, njs)


def test_direction_keeps_dots_and_rotates_arrows_by_angle_offset():
    assert note_direction(8, 45) == 8
    assert note_direction(1, 0) == 1
    assert note_direction(1, 90) == 3
    assert note_direction(0, -90) == 3
    assert note_direction(2, 45) == 6


def test_notes_outside_the_grid_are_dropped_and_ties_break_on_the_key():
    rows = ordered_notes([note(1.0, x=2, color=1), note(1.0, x=1, color=0), note(0.5, x=1500)])
    assert [row[1] for row in rows] == ["1010", "2011"]


def test_encoding_shape_and_colour_layout():
    encoded, times = encode_map([note(0.1, color=0), note(0.25, x=3, y=2, color=1, direction=8)])
    assert encoded.shape == (2, NOTE_SIZE)
    assert times == [0.1, 0.25]
    red, blue = encoded
    assert red[1 * 3 + 0] == 1.0
    assert red[12 + 1] == 1.0
    assert np.allclose(red[44:48], [0.8, 0.95, 0.8, 0.95])
    assert blue[22 + 3 * 3 + 2] == 1.0
    assert blue[34 + 8] == 1.0
    assert np.allclose(blue[44:48], [0.7, 0.925, 0.5, 0.875])
    assert np.isclose(blue[48], 10.0 / 30.0)


def test_segments_pad_the_ends_and_step_by_eight():
    encoded = np.ones((20, NOTE_SIZE))
    windows = segments(encoded)
    assert windows.shape == (2, 32, NOTE_SIZE)
    assert windows[0, :12].sum() == 0
    assert windows[0, 12:32].sum() == 20 * NOTE_SIZE
    assert windows[1, 8:12].sum() == 4 * NOTE_SIZE
    assert windows[1, 20:32].sum() == 4 * NOTE_SIZE


def test_timescale_applies_bpm_changes_from_the_change_beat_onward():
    scale = Timescale(120.0, [BpmChange(4.0, 60.0)])
    assert np.isclose(scale.to_seconds(4.0), 2.0)
    assert np.isclose(scale.to_seconds(6.0), 4.0)


def test_variable_njs_interpolates_between_events():
    vnjs = VariableNjs(10.0, [NjsEvent(0.0, 0.0, 0), NjsEvent(2.0, 4.0, 0)])
    assert vnjs.at(-1.0) == 10.0
    assert np.isclose(vnjs.at(1.0), 12.0)
    assert vnjs.at(3.0) == 14.0
