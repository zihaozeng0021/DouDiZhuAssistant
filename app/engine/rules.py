"""DouDizhu rules: move type detection, comparison, and legal action generation."""

from __future__ import annotations

import collections
import itertools

# global parameters
MIN_SINGLE_CARDS = 5
MIN_PAIRS = 3
MIN_TRIPLES = 2

# action types
TYPE_0_PASS = 0
TYPE_1_SINGLE = 1
TYPE_2_PAIR = 2
TYPE_3_TRIPLE = 3
TYPE_4_BOMB = 4
TYPE_5_KING_BOMB = 5
TYPE_6_3_1 = 6
TYPE_7_3_2 = 7
TYPE_8_SERIAL_SINGLE = 8
TYPE_9_SERIAL_PAIR = 9
TYPE_10_SERIAL_TRIPLE = 10
TYPE_11_SERIAL_3_1 = 11
TYPE_12_SERIAL_3_2 = 12
TYPE_13_4_2 = 13
TYPE_14_4_22 = 14
TYPE_15_WRONG = 15

MOVE_TYPES_WITH_LENGTH = {
    TYPE_8_SERIAL_SINGLE,
    TYPE_9_SERIAL_PAIR,
    TYPE_10_SERIAL_TRIPLE,
    TYPE_11_SERIAL_3_1,
    TYPE_12_SERIAL_3_2,
}


def select(cards: list[int], num: int) -> list[list[int]]:
    return [list(item) for item in itertools.combinations(cards, num)]


def is_continuous_seq(move: list[int]) -> bool:
    i = 0
    while i < len(move) - 1:
        if move[i + 1] - move[i] != 1:
            return False
        i += 1
    return True


def get_move_type(move: list[int]) -> dict[str, int]:
    move = sorted(move)
    move_size = len(move)
    move_dict = collections.Counter(move)

    if move_size == 0:
        return {"type": TYPE_0_PASS}

    if move_size == 1:
        return {"type": TYPE_1_SINGLE, "rank": move[0]}

    if move_size == 2:
        if move[0] == move[1]:
            return {"type": TYPE_2_PAIR, "rank": move[0]}
        if move == [20, 30]:
            return {"type": TYPE_5_KING_BOMB}
        return {"type": TYPE_15_WRONG}

    if move_size == 3:
        if len(move_dict) == 1:
            return {"type": TYPE_3_TRIPLE, "rank": move[0]}
        return {"type": TYPE_15_WRONG}

    if move_size == 4:
        if len(move_dict) == 1:
            return {"type": TYPE_4_BOMB, "rank": move[0]}
        if len(move_dict) == 2:
            if move[0] == move[1] == move[2] or move[1] == move[2] == move[3]:
                return {"type": TYPE_6_3_1, "rank": move[1]}
            return {"type": TYPE_15_WRONG}
        return {"type": TYPE_15_WRONG}

    if is_continuous_seq(move):
        return {"type": TYPE_8_SERIAL_SINGLE, "rank": move[0], "len": len(move)}

    if move_size == 5:
        if len(move_dict) == 2:
            return {"type": TYPE_7_3_2, "rank": move[2]}
        return {"type": TYPE_15_WRONG}

    count_dict: dict[int, int] = collections.defaultdict(int)
    for _, n in move_dict.items():
        count_dict[n] += 1

    if move_size == 6:
        if (len(move_dict) == 2 or len(move_dict) == 3) and count_dict.get(4) == 1 and (
            count_dict.get(2) == 1 or count_dict.get(1) == 2
        ):
            return {"type": TYPE_13_4_2, "rank": move[2]}

    if move_size == 8 and (
        ((len(move_dict) == 3 or len(move_dict) == 2) and (count_dict.get(4) == 1 and count_dict.get(2) == 2))
        or count_dict.get(4) == 2
    ):
        return {"type": TYPE_14_4_22, "rank": max(card for card, n in move_dict.items() if n == 4)}

    mdkeys = sorted(move_dict.keys())
    if len(move_dict) == count_dict.get(2) and is_continuous_seq(mdkeys):
        return {"type": TYPE_9_SERIAL_PAIR, "rank": mdkeys[0], "len": len(mdkeys)}

    if len(move_dict) == count_dict.get(3) and is_continuous_seq(mdkeys):
        return {"type": TYPE_10_SERIAL_TRIPLE, "rank": mdkeys[0], "len": len(mdkeys)}

    # Type 11 (serial 3+1) and Type 12 (serial 3+2)
    if count_dict.get(3, 0) >= MIN_TRIPLES:
        serial_3 = []
        single = []
        pair = []
        for card, n in move_dict.items():
            if n == 3:
                serial_3.append(card)
            elif n == 1:
                single.append(card)
            elif n == 2:
                pair.append(card)
            else:
                return {"type": TYPE_15_WRONG}

        serial_3.sort()
        if is_continuous_seq(serial_3):
            if len(serial_3) == len(single) + len(pair) * 2:
                return {"type": TYPE_11_SERIAL_3_1, "rank": serial_3[0], "len": len(serial_3)}
            if len(serial_3) == len(pair) and len(move_dict) == len(serial_3) * 2:
                return {"type": TYPE_12_SERIAL_3_2, "rank": serial_3[0], "len": len(serial_3)}

        if len(serial_3) == 4:
            if is_continuous_seq(serial_3[1:]):
                return {"type": TYPE_11_SERIAL_3_1, "rank": serial_3[1], "len": len(serial_3) - 1}
            if is_continuous_seq(serial_3[:-1]):
                return {"type": TYPE_11_SERIAL_3_1, "rank": serial_3[0], "len": len(serial_3) - 1}

    return {"type": TYPE_15_WRONG}


def _common_handle(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    new_moves = []
    for move in moves:
        if move[0] > rival_move[0]:
            new_moves.append(move)
    return new_moves


def _filter_type_1_single(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    return _common_handle(moves, rival_move)


def _filter_type_2_pair(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    return _common_handle(moves, rival_move)


def _filter_type_3_triple(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    return _common_handle(moves, rival_move)


def _filter_type_4_bomb(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    return _common_handle(moves, rival_move)


def _filter_type_6_3_1(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    rival_rank = sorted(rival_move)[1]
    new_moves = []
    for move in moves:
        if sorted(move)[1] > rival_rank:
            new_moves.append(move)
    return new_moves


def _filter_type_7_3_2(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    rival_rank = sorted(rival_move)[2]
    new_moves = []
    for move in moves:
        if sorted(move)[2] > rival_rank:
            new_moves.append(move)
    return new_moves


def _filter_type_8_serial_single(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    return _common_handle(moves, rival_move)


def _filter_type_9_serial_pair(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    return _common_handle(moves, rival_move)


def _filter_type_10_serial_triple(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    return _common_handle(moves, rival_move)


def _filter_type_11_serial_3_1(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    rival = collections.Counter(rival_move)
    rival_rank = max(card for card, count in rival.items() if count == 3)
    new_moves = []
    for move in moves:
        counter = collections.Counter(move)
        my_rank = max(card for card, count in counter.items() if count == 3)
        if my_rank > rival_rank:
            new_moves.append(move)
    return new_moves


def _filter_type_12_serial_3_2(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    rival = collections.Counter(rival_move)
    rival_rank = max(card for card, count in rival.items() if count == 3)
    new_moves = []
    for move in moves:
        counter = collections.Counter(move)
        my_rank = max(card for card, count in counter.items() if count == 3)
        if my_rank > rival_rank:
            new_moves.append(move)
    return new_moves


def _filter_type_13_4_2(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    rival_rank = sorted(rival_move)[2]
    new_moves = []
    for move in moves:
        if sorted(move)[2] > rival_rank:
            new_moves.append(move)
    return new_moves


def _filter_type_14_4_22(moves: list[list[int]], rival_move: list[int]) -> list[list[int]]:
    rival_counter = collections.Counter(rival_move)
    rival_rank = 0
    for card, count in rival_counter.items():
        if count == 4:
            rival_rank = card

    new_moves = []
    for move in moves:
        my_counter = collections.Counter(move)
        my_rank = 0
        for card, count in my_counter.items():
            if count == 4:
                my_rank = card
        if my_rank > rival_rank:
            new_moves.append(move)
    return new_moves


class MovesGener:
    """Generate all possible move combinations from a hand."""

    def __init__(self, cards_list: list[int]):
        self.cards_list = cards_list
        self.cards_dict: dict[int, int] = collections.defaultdict(int)
        for card in self.cards_list:
            self.cards_dict[card] += 1

        self.single_card_moves: list[list[int]] = []
        self.gen_type_1_single()
        self.pair_moves: list[list[int]] = []
        self.gen_type_2_pair()
        self.triple_cards_moves: list[list[int]] = []
        self.gen_type_3_triple()
        self.bomb_moves: list[list[int]] = []
        self.gen_type_4_bomb()
        self.final_bomb_moves: list[list[int]] = []
        self.gen_type_5_king_bomb()

    def _gen_serial_moves(
        self,
        cards: list[int],
        min_serial: int,
        repeat: int = 1,
        repeat_num: int = 0,
    ) -> list[list[int]]:
        if repeat_num < min_serial:
            repeat_num = 0

        single_cards = sorted(list(set(cards)))
        seq_records: list[tuple[int, int]] = []
        moves: list[list[int]] = []

        start = i = 0
        longest = 1
        while i < len(single_cards):
            if i + 1 < len(single_cards) and single_cards[i + 1] - single_cards[i] == 1:
                longest += 1
                i += 1
            else:
                seq_records.append((start, longest))
                i += 1
                start = i
                longest = 1

        for seq in seq_records:
            if seq[1] < min_serial:
                continue
            start, longest = seq[0], seq[1]
            longest_list = single_cards[start : start + longest]

            if repeat_num == 0:
                steps = min_serial
                while steps <= longest:
                    index = 0
                    while steps + index <= longest:
                        target_moves = sorted(longest_list[index : index + steps] * repeat)
                        moves.append(target_moves)
                        index += 1
                    steps += 1
            else:
                if longest < repeat_num:
                    continue
                index = 0
                while index + repeat_num <= longest:
                    target_moves = sorted(longest_list[index : index + repeat_num] * repeat)
                    moves.append(target_moves)
                    index += 1

        return moves

    def gen_type_1_single(self) -> list[list[int]]:
        self.single_card_moves = [[card] for card in set(self.cards_list)]
        return self.single_card_moves

    def gen_type_2_pair(self) -> list[list[int]]:
        self.pair_moves = []
        for card, count in self.cards_dict.items():
            if count >= 2:
                self.pair_moves.append([card, card])
        return self.pair_moves

    def gen_type_3_triple(self) -> list[list[int]]:
        self.triple_cards_moves = []
        for card, count in self.cards_dict.items():
            if count >= 3:
                self.triple_cards_moves.append([card, card, card])
        return self.triple_cards_moves

    def gen_type_4_bomb(self) -> list[list[int]]:
        self.bomb_moves = []
        for card, count in self.cards_dict.items():
            if count == 4:
                self.bomb_moves.append([card, card, card, card])
        return self.bomb_moves

    def gen_type_5_king_bomb(self) -> list[list[int]]:
        self.final_bomb_moves = []
        if 20 in self.cards_list and 30 in self.cards_list:
            self.final_bomb_moves.append([20, 30])
        return self.final_bomb_moves

    def gen_type_6_3_1(self) -> list[list[int]]:
        result = []
        for single in self.single_card_moves:
            for triple in self.triple_cards_moves:
                if single[0] != triple[0]:
                    result.append(single + triple)
        return result

    def gen_type_7_3_2(self) -> list[list[int]]:
        result: list[list[int]] = []
        for pair in self.pair_moves:
            for triple in self.triple_cards_moves:
                if pair[0] != triple[0]:
                    result.append(pair + triple)
        return result

    def gen_type_8_serial_single(self, repeat_num: int = 0) -> list[list[int]]:
        return self._gen_serial_moves(self.cards_list, MIN_SINGLE_CARDS, repeat=1, repeat_num=repeat_num)

    def gen_type_9_serial_pair(self, repeat_num: int = 0) -> list[list[int]]:
        single_pairs = [card for card, count in self.cards_dict.items() if count >= 2]
        return self._gen_serial_moves(single_pairs, MIN_PAIRS, repeat=2, repeat_num=repeat_num)

    def gen_type_10_serial_triple(self, repeat_num: int = 0) -> list[list[int]]:
        single_triples = [card for card, count in self.cards_dict.items() if count >= 3]
        return self._gen_serial_moves(single_triples, MIN_TRIPLES, repeat=3, repeat_num=repeat_num)

    def gen_type_11_serial_3_1(self, repeat_num: int = 0) -> list[list[int]]:
        serial_3_moves = self.gen_type_10_serial_triple(repeat_num=repeat_num)
        serial_3_1_moves = []
        for serial_3 in serial_3_moves:
            serial_3_set = set(serial_3)
            new_cards = [card for card in self.cards_list if card not in serial_3_set]
            subcards = select(new_cards, len(serial_3_set))
            for subcard in subcards:
                serial_3_1_moves.append(serial_3 + subcard)
        return [group for group, _ in itertools.groupby(serial_3_1_moves)]

    def gen_type_12_serial_3_2(self, repeat_num: int = 0) -> list[list[int]]:
        serial_3_moves = self.gen_type_10_serial_triple(repeat_num=repeat_num)
        serial_3_2_moves = []
        pair_set = sorted([card for card, count in self.cards_dict.items() if count >= 2])
        for serial_3 in serial_3_moves:
            serial_3_set = set(serial_3)
            pair_candidates = [card for card in pair_set if card not in serial_3_set]
            subcards = select(pair_candidates, len(serial_3_set))
            for subcard in subcards:
                serial_3_2_moves.append(sorted(serial_3 + subcard * 2))
        return serial_3_2_moves

    def gen_type_13_4_2(self) -> list[list[int]]:
        four_cards = [card for card, count in self.cards_dict.items() if count == 4]
        result = []
        for four_card in four_cards:
            cards_list = [card for card in self.cards_list if card != four_card]
            subcards = select(cards_list, 2)
            for subcard in subcards:
                result.append([four_card] * 4 + subcard)
        return [group for group, _ in itertools.groupby(result)]

    def gen_type_14_4_22(self) -> list[list[int]]:
        four_cards = [card for card, count in self.cards_dict.items() if count == 4]
        result = []
        for four_card in four_cards:
            cards_list = [card for card, count in self.cards_dict.items() if card != four_card and count >= 2]
            subcards = select(cards_list, 2)
            for subcard in subcards:
                result.append([four_card] * 4 + [subcard[0], subcard[0], subcard[1], subcard[1]])
        return result

    def gen_moves(self) -> list[list[int]]:
        moves = []
        moves.extend(self.gen_type_1_single())
        moves.extend(self.gen_type_2_pair())
        moves.extend(self.gen_type_3_triple())
        moves.extend(self.gen_type_4_bomb())
        moves.extend(self.gen_type_5_king_bomb())
        moves.extend(self.gen_type_6_3_1())
        moves.extend(self.gen_type_7_3_2())
        moves.extend(self.gen_type_8_serial_single())
        moves.extend(self.gen_type_9_serial_pair())
        moves.extend(self.gen_type_10_serial_triple())
        moves.extend(self.gen_type_11_serial_3_1())
        moves.extend(self.gen_type_12_serial_3_2())
        moves.extend(self.gen_type_13_4_2())
        moves.extend(self.gen_type_14_4_22())
        return moves


def get_rival_move(action_sequence: list[list[int]]) -> list[int]:
    if not action_sequence:
        return []
    if len(action_sequence[-1]) == 0:
        if len(action_sequence) >= 2:
            return action_sequence[-2]
        return []
    return action_sequence[-1]


def get_legal_actions(hand_cards: list[int], action_sequence: list[list[int]]) -> list[list[int]]:
    mg = MovesGener(hand_cards)
    rival_move = get_rival_move(action_sequence)
    rival_type = get_move_type(rival_move)
    rival_move_type = rival_type["type"]
    rival_move_len = rival_type.get("len", 1)
    moves: list[list[int]] = []

    if rival_move_type == TYPE_0_PASS:
        moves = mg.gen_moves()
    elif rival_move_type == TYPE_1_SINGLE:
        all_moves = mg.gen_type_1_single()
        moves = _filter_type_1_single(all_moves, rival_move)
    elif rival_move_type == TYPE_2_PAIR:
        all_moves = mg.gen_type_2_pair()
        moves = _filter_type_2_pair(all_moves, rival_move)
    elif rival_move_type == TYPE_3_TRIPLE:
        all_moves = mg.gen_type_3_triple()
        moves = _filter_type_3_triple(all_moves, rival_move)
    elif rival_move_type == TYPE_4_BOMB:
        all_moves = mg.gen_type_4_bomb() + mg.gen_type_5_king_bomb()
        moves = _filter_type_4_bomb(all_moves, rival_move)
    elif rival_move_type == TYPE_5_KING_BOMB:
        moves = []
    elif rival_move_type == TYPE_6_3_1:
        all_moves = mg.gen_type_6_3_1()
        moves = _filter_type_6_3_1(all_moves, rival_move)
    elif rival_move_type == TYPE_7_3_2:
        all_moves = mg.gen_type_7_3_2()
        moves = _filter_type_7_3_2(all_moves, rival_move)
    elif rival_move_type == TYPE_8_SERIAL_SINGLE:
        all_moves = mg.gen_type_8_serial_single(repeat_num=rival_move_len)
        moves = _filter_type_8_serial_single(all_moves, rival_move)
    elif rival_move_type == TYPE_9_SERIAL_PAIR:
        all_moves = mg.gen_type_9_serial_pair(repeat_num=rival_move_len)
        moves = _filter_type_9_serial_pair(all_moves, rival_move)
    elif rival_move_type == TYPE_10_SERIAL_TRIPLE:
        all_moves = mg.gen_type_10_serial_triple(repeat_num=rival_move_len)
        moves = _filter_type_10_serial_triple(all_moves, rival_move)
    elif rival_move_type == TYPE_11_SERIAL_3_1:
        all_moves = mg.gen_type_11_serial_3_1(repeat_num=rival_move_len)
        moves = _filter_type_11_serial_3_1(all_moves, rival_move)
    elif rival_move_type == TYPE_12_SERIAL_3_2:
        all_moves = mg.gen_type_12_serial_3_2(repeat_num=rival_move_len)
        moves = _filter_type_12_serial_3_2(all_moves, rival_move)
    elif rival_move_type == TYPE_13_4_2:
        all_moves = mg.gen_type_13_4_2()
        moves = _filter_type_13_4_2(all_moves, rival_move)
    elif rival_move_type == TYPE_14_4_22:
        all_moves = mg.gen_type_14_4_22()
        moves = _filter_type_14_4_22(all_moves, rival_move)

    if rival_move_type not in [TYPE_0_PASS, TYPE_4_BOMB, TYPE_5_KING_BOMB]:
        moves = moves + mg.gen_type_4_bomb() + mg.gen_type_5_king_bomb()

    if len(rival_move) != 0:
        moves = moves + [[]]

    for move in moves:
        move.sort()
    return moves


def is_bomb(action: list[int]) -> bool:
    action_type = get_move_type(action)["type"]
    return action_type in {TYPE_4_BOMB, TYPE_5_KING_BOMB}


def is_action_compatible_with_rival(action: list[int], rival_move: list[int]) -> bool:
    """
    Check whether `action` can be legally played against `rival_move`,
    without using hidden hand information.
    """
    action = sorted(action)
    rival_move = sorted(rival_move)

    if not action:
        return len(rival_move) != 0

    action_info = get_move_type(action)
    action_type = action_info["type"]
    if action_type == TYPE_15_WRONG:
        return False

    if not rival_move:
        return True

    rival_info = get_move_type(rival_move)
    rival_type = rival_info["type"]

    if action_type == TYPE_5_KING_BOMB:
        return rival_type != TYPE_5_KING_BOMB

    if action_type == TYPE_4_BOMB:
        if rival_type == TYPE_5_KING_BOMB:
            return False
        if rival_type == TYPE_4_BOMB:
            return action_info["rank"] > rival_info["rank"]
        return True

    if rival_type in {TYPE_4_BOMB, TYPE_5_KING_BOMB}:
        return False

    if action_type != rival_type:
        return False

    if action_type in MOVE_TYPES_WITH_LENGTH and action_info.get("len") != rival_info.get("len"):
        return False

    return action_info.get("rank", -1) > rival_info.get("rank", -1)

