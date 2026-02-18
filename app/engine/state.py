"""Game state for partial-information DouZero assistant."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from .parser import DECK_COUNTER, action_to_text
from .rules import get_legal_actions, get_move_type, get_rival_move, is_action_compatible_with_rival, is_bomb

ROLE_ORDER = ["landlord", "landlord_down", "landlord_up"]
Role = str


class ValidationError(ValueError):
    """Raised when game action/state is invalid."""


def next_role(role: Role) -> Role:
    idx = ROLE_ORDER.index(role)
    return ROLE_ORDER[(idx + 1) % len(ROLE_ORDER)]


def flatten_counter(counter: Counter[int]) -> list[int]:
    cards: list[int] = []
    for card in sorted(counter.keys()):
        cards.extend([card] * counter[card])
    return cards


@dataclass(frozen=True)
class GameConfig:
    user_role: Role
    initial_my_hand: list[int]
    initial_three_landlord_cards: list[int]


class GameState:
    """Mutable game state with replay-based undo."""

    def __init__(self, config: GameConfig):
        self.config = config
        self.action_log: list[dict[str, Any]] = []
        self._validate_initial_config(config)
        self._reset_runtime_state()

    @classmethod
    def create(cls, user_role: Role, my_hand: list[int], three_landlord_cards: list[int]) -> "GameState":
        config = GameConfig(
            user_role=user_role,
            initial_my_hand=sorted(my_hand),
            initial_three_landlord_cards=sorted(three_landlord_cards),
        )
        return cls(config)

    def _validate_initial_config(self, config: GameConfig) -> None:
        if config.user_role not in ROLE_ORDER:
            raise ValidationError(f"Unsupported role: {config.user_role}")

        expected_count = 17
        if len(config.initial_my_hand) != expected_count:
            raise ValidationError(
                f"Role '{config.user_role}' expects {expected_count} cards in my_hand, got {len(config.initial_my_hand)}."
            )

        if len(config.initial_three_landlord_cards) != 3:
            raise ValidationError("three_landlord_cards must contain exactly 3 cards.")

        known_counter = Counter(config.initial_my_hand)
        known_counter.update(config.initial_three_landlord_cards)

        for card, count in known_counter.items():
            if count > DECK_COUNTER[card]:
                raise ValidationError(f"Card count exceeds deck limit for {card}: {count}")

    def _reset_runtime_state(self) -> None:
        self.user_role: Role = self.config.user_role
        self.acting_role: Role = "landlord"
        self.my_hand_cards: list[int] = list(self.config.initial_my_hand)
        if self.user_role == "landlord":
            # Landlord starts with 17 hand cards and receives 3 bottom cards.
            self.my_hand_cards.extend(self.config.initial_three_landlord_cards)
            self.my_hand_cards.sort()
        self.three_landlord_cards: list[int] = list(self.config.initial_three_landlord_cards)
        self.card_play_action_seq: list[list[int]] = []
        self.played_cards: dict[Role, list[int]] = {role: [] for role in ROLE_ORDER}
        self.last_move_dict: dict[Role, list[int]] = {role: [] for role in ROLE_ORDER}
        self.num_cards_left_dict: dict[Role, int] = {
            "landlord": 20,
            "landlord_down": 17,
            "landlord_up": 17,
        }
        self.last_pid: Role = "landlord"
        self.bomb_num: int = 0
        self.game_over: bool = False
        self.winner: str | None = None

    def _remaining_unseen_counter(self) -> Counter[int]:
        counter = Counter(DECK_COUNTER)
        counter.subtract(self.my_hand_cards)
        for role in ROLE_ORDER:
            counter.subtract(self.played_cards[role])
        for card in list(counter.keys()):
            if counter[card] <= 0:
                del counter[card]
        return counter

    def _remaining_unseen_cards(self) -> list[int]:
        return flatten_counter(self._remaining_unseen_counter())

    def get_last_move(self) -> list[int]:
        return get_rival_move(self.card_play_action_seq)

    def get_last_two_moves(self) -> list[list[int]]:
        last_two_moves = [[], []]
        for action in self.card_play_action_seq[-2:]:
            last_two_moves.insert(0, action)
            last_two_moves = last_two_moves[:2]
        return [list(last_two_moves[0]), list(last_two_moves[1])]

    def need_user_action(self) -> bool:
        return not self.game_over and self.acting_role == self.user_role

    def legal_actions_for_user(self) -> list[list[int]]:
        if not self.need_user_action():
            return []
        return get_legal_actions(self.my_hand_cards, self.card_play_action_seq)

    def build_infoset_for_user(self) -> SimpleNamespace:
        if not self.need_user_action():
            raise ValidationError("Cannot build infoset: not user's turn.")

        legal_actions = self.legal_actions_for_user()
        unseen_cards = self._remaining_unseen_cards()
        all_handcards = {role: [] for role in ROLE_ORDER}
        all_handcards[self.user_role] = list(self.my_hand_cards)
        infoset = SimpleNamespace(
            player_position=self.user_role,
            player_hand_cards=list(self.my_hand_cards),
            num_cards_left_dict=dict(self.num_cards_left_dict),
            three_landlord_cards=list(self.three_landlord_cards),
            card_play_action_seq=[list(action) for action in self.card_play_action_seq],
            other_hand_cards=unseen_cards,
            legal_actions=[list(action) for action in legal_actions],
            last_move=list(self.get_last_move()),
            last_two_moves=[list(action) for action in self.get_last_two_moves()],
            last_move_dict={role: list(action) for role, action in self.last_move_dict.items()},
            played_cards={role: list(cards) for role, cards in self.played_cards.items()},
            all_handcards=all_handcards,
            last_pid=self.last_pid,
            bomb_num=self.bomb_num,
        )
        return infoset

    def _validate_user_action(self, action: list[int]) -> None:
        legal_actions = self.legal_actions_for_user()
        if action not in legal_actions:
            raise ValidationError(f"Invalid action for your turn: {action_to_text(action)}")

    def _validate_opponent_action(self, action: list[int]) -> None:
        actor = self.acting_role
        rival_move = self.get_last_move()

        if not action:
            if not rival_move:
                raise ValidationError("PASS is not allowed when leading a new round.")
            return

        if len(action) > self.num_cards_left_dict[actor]:
            raise ValidationError(f"{actor} does not have enough cards left for this action.")

        if get_move_type(action)["type"] == 15:
            raise ValidationError("Opponent action is not a valid DouDizhu move.")

        if not is_action_compatible_with_rival(action, rival_move):
            raise ValidationError("Opponent action cannot beat current rival move.")

        unseen_counter = self._remaining_unseen_counter()
        action_counter = Counter(action)
        for card, count in action_counter.items():
            if count > unseen_counter[card]:
                raise ValidationError("Opponent action exceeds visible remaining card pool.")

    def apply_action(self, action: list[int], validate: bool = True, record: bool = True) -> None:
        if self.game_over:
            raise ValidationError("Game already over.")
        if self.acting_role not in ROLE_ORDER:
            raise ValidationError(f"Unknown acting role: {self.acting_role}")

        action = sorted(action)
        actor = self.acting_role

        if validate:
            if actor == self.user_role:
                self._validate_user_action(action)
            else:
                self._validate_opponent_action(action)

        if record:
            self.action_log.append({"actor": actor, "action": list(action)})

        self.last_move_dict[actor] = list(action)
        self.card_play_action_seq.append(list(action))

        if action:
            if actor == self.user_role:
                for card in action:
                    try:
                        self.my_hand_cards.remove(card)
                    except ValueError as exc:
                        raise ValidationError("Your action uses cards not in your hand.") from exc

            self.played_cards[actor].extend(action)
            self.num_cards_left_dict[actor] -= len(action)
            if self.num_cards_left_dict[actor] < 0:
                raise ValidationError(f"{actor} card count dropped below zero.")

            if actor == "landlord" and self.three_landlord_cards:
                for card in action:
                    if card in self.three_landlord_cards:
                        self.three_landlord_cards.remove(card)

            self.last_pid = actor

        if is_bomb(action):
            self.bomb_num += 1

        self._check_game_over()
        if not self.game_over:
            self.acting_role = next_role(self.acting_role)

    def _check_game_over(self) -> None:
        for role, cards_left in self.num_cards_left_dict.items():
            if cards_left == 0:
                self.game_over = True
                self.winner = "landlord" if role == "landlord" else "farmer"
                return

    def undo(self) -> None:
        if not self.action_log:
            raise ValidationError("No action to undo.")
        self.action_log.pop()
        replay_actions = [list(entry["action"]) for entry in self.action_log]
        self._reset_runtime_state()
        old_log = replay_actions
        self.action_log = []
        for action in old_log:
            self.apply_action(action, validate=False, record=True)

    def snapshot(self) -> dict[str, Any]:
        return {
            "user_role": self.user_role,
            "acting_role": self.acting_role,
            "my_hand_text": action_to_text(self.my_hand_cards),
            "num_cards_left_dict": dict(self.num_cards_left_dict),
            "played_cards_text": {role: action_to_text(cards) for role, cards in self.played_cards.items()},
            "last_move_dict_text": {role: action_to_text(action) for role, action in self.last_move_dict.items()},
            "card_play_action_seq_text": [action_to_text(action) for action in self.card_play_action_seq],
            "bomb_num": self.bomb_num,
            "last_pid": self.last_pid,
            "three_landlord_cards_text": action_to_text(self.three_landlord_cards),
            "game_over": self.game_over,
            "winner": self.winner,
            "need_user_action": self.need_user_action(),
            "action_log": [
                {"step": i + 1, "actor": entry["actor"], "text": action_to_text(entry["action"])}
                for i, entry in enumerate(self.action_log)
            ],
        }
