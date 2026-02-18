from app.engine.rules import (
    TYPE_15_WRONG,
    TYPE_1_SINGLE,
    TYPE_2_PAIR,
    TYPE_4_BOMB,
    TYPE_5_KING_BOMB,
    get_legal_actions,
    get_move_type,
    is_action_compatible_with_rival,
)
from app.engine.parser import parse_action_text


def test_get_move_type_basics():
    assert get_move_type(parse_action_text("3"))["type"] == TYPE_1_SINGLE
    assert get_move_type(parse_action_text("44"))["type"] == TYPE_2_PAIR
    assert get_move_type(parse_action_text("7777"))["type"] == TYPE_4_BOMB
    assert get_move_type(parse_action_text("XD"))["type"] == TYPE_5_KING_BOMB
    assert get_move_type(parse_action_text("34"))["type"] == TYPE_15_WRONG


def test_action_compatibility():
    assert is_action_compatible_with_rival(parse_action_text("5"), parse_action_text("4")) is True
    assert is_action_compatible_with_rival(parse_action_text("3"), parse_action_text("4")) is False
    assert is_action_compatible_with_rival([], parse_action_text("4")) is True
    assert is_action_compatible_with_rival([], []) is False
    assert is_action_compatible_with_rival(parse_action_text("XD"), parse_action_text("7777")) is True


def test_get_legal_actions_follow_single():
    hand = parse_action_text("345XD")
    action_seq = [parse_action_text("4")]
    legal = get_legal_actions(hand, action_seq)

    assert parse_action_text("5") in legal
    assert parse_action_text("X") in legal
    assert parse_action_text("D") in legal
    assert parse_action_text("XD") in legal
    assert [] in legal
    assert parse_action_text("3") not in legal
