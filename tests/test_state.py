import pytest

from app.engine.parser import parse_action_text
from app.engine.state import GameState, ValidationError


def test_state_apply_and_undo():
    state = GameState.create(
        "landlord",
        parse_action_text("33334444556678910JQXD"),
        parse_action_text("3XD"),
    )

    assert state.need_user_action() is True
    state.apply_action(parse_action_text("5"))  # user landlord leads
    assert state.acting_role == "landlord_down"
    assert state.need_user_action() is False

    state.apply_action(parse_action_text("6"))  # opponent follows
    assert state.acting_role == "landlord_up"
    assert len(state.action_log) == 2

    state.undo()
    assert state.acting_role == "landlord_down"
    assert len(state.action_log) == 1


def test_opponent_cannot_pass_when_leading():
    state = GameState.create(
        "landlord_up",
        parse_action_text("3344556678910JQKA2"),
        parse_action_text("2XD"),
    )

    # First turn is landlord, not user.
    with pytest.raises(ValidationError):
        state.apply_action([])
