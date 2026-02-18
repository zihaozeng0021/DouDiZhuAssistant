import pytest

from app.engine.parser import ParseError, action_to_text, parse_action_click, parse_action_payload, parse_action_text


def test_parse_action_text_basic():
    assert parse_action_text("334455") == [3, 3, 4, 4, 5, 5]
    assert action_to_text(parse_action_text("10JQKA2XD")) == "10JQKA2XD"
    assert parse_action_text("pass") == []


def test_parse_action_click():
    result = parse_action_click({"3": 2, "A": 1, "X": 1})
    assert result == [3, 3, 14, 20]


def test_parse_action_payload_list_sorting():
    with pytest.raises(ParseError):
        parse_action_payload([14, 3, 3])


def test_parse_action_text_invalid():
    with pytest.raises(ParseError):
        parse_action_text("33Z")


def test_parse_action_reject_more_than_four_same_rank():
    with pytest.raises(ParseError):
        parse_action_text("33333")


def test_parse_action_click_reject_more_than_four_same_rank():
    with pytest.raises(ParseError):
        parse_action_click({"Q": 5})
