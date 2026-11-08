"""Generators run with many seeds: a rare bad question would otherwise reach production."""

from random import Random

import pytest

from apps.games.generators import (
    generate_memory,
    generate_missing_number,
    generate_pattern,
    replay_memory,
)

SEEDS = range(200)
LEVELS = ["easy", "medium", "hard"]
SHAPE_TYPES = {"circle", "square", "triangle", "star", "diamond", "hexagon", "arrow"}
SHAPE_COLORS = {"teal", "yellow", "pink", "blue", "orange", "purple"}


@pytest.mark.parametrize("level,pairs", [("easy", 4), ("medium", 6), ("hard", 8)])
def test_memory_board_is_made_of_pairs(level, pairs):
    for seed in SEEDS:
        content = generate_memory(Random(seed), level)
        faces = [card["face"] for card in content["cards"]]
        assert content["pairs"] == pairs
        assert len(faces) == pairs * 2
        assert all(faces.count(face) == 2 for face in faces)
        assert len({card["id"] for card in content["cards"]}) == pairs * 2


@pytest.mark.parametrize("level", LEVELS)
def test_missing_number_questions_are_well_formed(level):
    for seed in SEEDS:
        questions = generate_missing_number(Random(seed), level)["questions"]
        assert len(questions) == 8
        for question in questions:
            values = [option["value"] for option in question["options"]]
            assert len(values) == len(set(values)) == 4
            assert all(value >= 0 for value in values)
            assert question["sequence"].count(None) == 1
            assert question["sequence"][0] is not None  # the rule must stay visible
            assert question["correct_option_id"] in {o["id"] for o in question["options"]}
            assert question["explanation"]


def test_missing_number_correct_option_is_the_hidden_term():
    question = generate_missing_number(Random(1), "easy")["questions"][0]
    hidden = question["sequence"].index(None)
    correct = next(o for o in question["options"] if o["id"] == question["correct_option_id"])
    # Easy sequences are arithmetic: the step between visible neighbours gives the hidden term.
    terms = question["sequence"]
    step = next(
        terms[i + 1] - terms[i]
        for i in range(len(terms) - 1)
        if terms[i] is not None and terms[i + 1] is not None
    )
    assert correct["value"] == terms[0] + step * hidden


@pytest.mark.parametrize("level", LEVELS)
def test_pattern_questions_are_well_formed(level):
    for seed in SEEDS:
        questions = generate_pattern(Random(seed), level)["questions"]
        assert len(questions) == 6
        for question in questions:
            assert len(question["options"]) == 4
            assert question["sequence"][-1] is None
            shapes = [option["shape"] for option in question["options"]]
            keys = {(s["type"], s["color"], s["rotation"], s["count"]) for s in shapes}
            assert len(keys) == 4, "wrong options must differ from the answer and each other"
            for shape in [*shapes, *question["sequence"][:-1]]:
                assert shape["type"] in SHAPE_TYPES
                assert shape["color"] in SHAPE_COLORS
                assert 1 <= shape["count"] <= 4


def test_same_seed_gives_same_content():
    assert generate_pattern(Random(7), "hard") == generate_pattern(Random(7), "hard")


CARDS = [
    {"id": "c1", "face": "cat"},
    {"id": "c2", "face": "sun"},
    {"id": "c3", "face": "cat"},
    {"id": "c4", "face": "sun"},
]


def test_replay_accepts_a_solving_log_with_misses():
    replay = replay_memory(CARDS, [["c1", "c2"], ["c1", "c3"], ["c2", "c4"]])
    assert (replay.valid, replay.moves, replay.matched_pairs) == (True, 3, 2)


@pytest.mark.parametrize(
    "moves",
    [
        None,
        "x",
        {},
        [["c1", "c3"]],  # board not solved
        [["c1", "c3"], ["c1", "c3"], ["c2", "c4"]],  # reuses matched cards
        [["c1", "c9"]],  # unknown card
        [["c1", "c1"]],  # same card twice
        [["c1"]],  # malformed move
        [[1, 2]],  # wrong types
        [["c1", "c2"]] * 501 + [["c1", "c3"], ["c2", "c4"]],  # absurdly long log
    ],
)
def test_replay_rejects_bad_logs(moves):
    assert replay_memory(CARDS, moves).valid is False
