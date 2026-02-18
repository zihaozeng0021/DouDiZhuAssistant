"""Parsing utilities for cards/actions and display formatting."""

from __future__ import annotations

from collections import Counter
from typing import Any

VALID_CARDS = {3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 20, 30}
MAX_COUNT_PER_RANK = 4

TEXT_TO_CARD = {
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "T": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14,
    "2": 17,
    "X": 20,
    "D": 30,
}

CARD_TO_TEXT = {
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "10",
    11: "J",
    12: "Q",
    13: "K",
    14: "A",
    17: "2",
    20: "X",
    30: "D",
}

DECK_COUNTER = Counter(
    {
        3: 4,
        4: 4,
        5: 4,
        6: 4,
        7: 4,
        8: 4,
        9: 4,
        10: 4,
        11: 4,
        12: 4,
        13: 4,
        14: 4,
        17: 4,
        20: 1,
        30: 1,
    }
)


class ParseError(ValueError):
    """Raised when action/hand payload cannot be parsed."""


def _tokenize_text_cards(text: str) -> list[str]:
    payload = text.strip().upper().replace(" ", "")
    if payload in {"PASS", "P"}:
        return []

    tokens: list[str] = []
    i = 0
    while i < len(payload):
        if payload.startswith("10", i):
            tokens.append("10")
            i += 2
            continue

        token = payload[i]
        if token in TEXT_TO_CARD:
            tokens.append(token)
            i += 1
            continue

        raise ParseError(f"Invalid card token: {payload[i:]}")

    return tokens


def parse_action_text(text: str) -> list[int]:
    """Parse action from text input. PASS/P -> []."""
    if text is None:
        raise ParseError("Action text is required.")
    tokens = _tokenize_text_cards(text)
    if not tokens:
        return []
    cards = [TEXT_TO_CARD[token] for token in tokens]
    validate_cards_max_four(cards, "action")
    cards.sort()
    return cards


def parse_action_click(counts: dict[str, Any]) -> list[int]:
    """Parse action from click payload like {'3': 2, 'A': 1}."""
    if not isinstance(counts, dict):
        raise ParseError("Click payload must be an object.")

    cards: list[int] = []
    for rank, raw_count in counts.items():
        key = str(rank).strip().upper()
        if key == "T":
            key = "10"
        if key not in TEXT_TO_CARD:
            raise ParseError(f"Unsupported rank: {rank}")

        try:
            count = int(raw_count)
        except (TypeError, ValueError) as exc:
            raise ParseError(f"Invalid count for {rank}: {raw_count}") from exc
        if count < 0:
            raise ParseError(f"Negative count is not allowed: {rank}={count}")

        cards.extend([TEXT_TO_CARD[key]] * count)

    validate_cards_max_four(cards, "action")
    cards.sort()
    return cards


def parse_action_payload(payload: Any) -> list[int]:
    """
    Parse action payload in one of formats:
    - "3344", "PASS"
    - {"3": 2, "4": 2}
    - {"counts": {"3": 2, "4": 2}}
    - {"type": "pass"}
    """
    if payload is None:
        raise ParseError("Action payload is required.")

    if isinstance(payload, str):
        return parse_action_text(payload)

    if isinstance(payload, dict):
        if str(payload.get("type", "")).lower() == "pass":
            return []
        if "counts" in payload:
            return parse_action_click(payload["counts"])
        return parse_action_click(payload)

    raise ParseError("Unsupported action payload format. Use text like '3344'/'PASS' or click counts object.")


def parse_hand_payload(payload: Any, field_name: str) -> list[int]:
    """Parse hand-like payload. PASS is forbidden."""
    cards = parse_action_payload(payload)
    if len(cards) == 0:
        raise ParseError(f"{field_name} cannot be empty/PASS.")
    if any(card not in VALID_CARDS for card in cards):
        raise ParseError(f"{field_name} contains unsupported cards.")
    validate_cards_max_four(cards, field_name)
    return cards


def validate_cards_max_four(cards: list[int], field_name: str) -> None:
    counter = Counter(cards)
    for card, count in counter.items():
        if count > MAX_COUNT_PER_RANK:
            symbol = CARD_TO_TEXT.get(card, str(card))
            raise ParseError(f"{field_name} rank '{symbol}' exceeds {MAX_COUNT_PER_RANK} cards ({count}).")


def validate_cards_not_exceed_deck(cards: list[int], field_name: str) -> None:
    counter = Counter(cards)
    for card, count in counter.items():
        if count > DECK_COUNTER[card]:
            symbol = CARD_TO_TEXT.get(card, str(card))
            raise ParseError(f"{field_name} has too many '{symbol}' cards ({count}).")


def action_to_text(action: list[int]) -> str:
    if not action:
        return "PASS"
    return "".join(CARD_TO_TEXT[card] for card in sorted(action))


def actions_to_text(actions: list[list[int]]) -> list[str]:
    return [action_to_text(action) for action in actions]
