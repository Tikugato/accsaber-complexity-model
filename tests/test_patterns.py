from complexity_model.beatmap import Note
from complexity_model.patterns import swing_shares


def note(seconds, color=0, direction=1, x=1, y=0):
    return Note(seconds, x, y, color, direction, 0, 10.0)


def test_alternating_down_and_dot_is_all_resets():
    notes = [note(0.0, 1, 1), note(0.8, 1, 8), note(1.6, 0, 1), note(2.4, 0, 8), note(3.2, 1, 1), note(4.0, 0, 1)]
    shares = swing_shares(notes)
    assert shares.reset_share == 1.0
    assert shares.dot_share == 2 / 6
    assert shares.pairs == 4


def test_down_up_flow_has_no_resets():
    notes = [note(0.0, 0, 1), note(0.5, 0, 0), note(1.0, 0, 1), note(1.5, 0, 0)]
    shares = swing_shares(notes)
    assert shares.reset_share == 0.0
    assert shares.dot_share == 0.0


def test_diagonals_count_by_direction_and_stacks_are_skipped():
    notes = [note(0.0, 0, 1), note(0.0, 0, 6), note(0.5, 0, 7), note(1.0, 0, 1), note(1.5, 0, 0)]
    shares = swing_shares(notes)
    assert shares.pairs == 3
    assert shares.reset_share == 1 / 3


def test_bottom_row_up_swings_are_counted():
    notes = [
        note(0.0, 0, 0, x=0, y=0),
        note(0.5, 0, 4, x=3, y=0),
        note(1.0, 0, 5, x=0, y=0),
        note(1.5, 0, 0, x=1, y=0),
        note(2.0, 0, 0, x=0, y=1),
        note(2.5, 0, 1, x=0, y=0),
    ]
    shares = swing_shares(notes)
    assert shares.bottom_up_share == 4 / 6


def test_up_swings_above_the_bottom_row_do_not_count():
    notes = [note(0.0, 0, 1, y=0), note(0.5, 0, 0, y=1), note(1.0, 0, 4, y=2)]
    assert swing_shares(notes).bottom_up_share == 0.0


def test_empty_map():
    shares = swing_shares([])
    assert shares.reset_share == 0.0 and shares.dot_share == 0.0 and shares.pairs == 0
    assert shares.bottom_up_share == 0.0
