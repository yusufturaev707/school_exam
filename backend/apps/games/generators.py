"""
Generates game content for each session. Pure Python with no Django or database, so it's easy to
test: pass in `random.Random(seed)` and the output is reproducible.

Each question stores `correct_option_id` and `explanation`, which stay on the server until the
question is answered. `public_content()` in services.py removes them before anything is sent.
Keys such as `sequence`, `options` and `shape` are sent to the client as they are.
"""

from collections.abc import Callable
from dataclasses import dataclass
from random import Random
from typing import Any

# ============================================================================ memory

MEMORY_FACES = ["apple", "cat", "fish", "rocket", "sun", "moon", "bird", "flower", "star", "tree"]
MEMORY_PAIRS = {"easy": 4, "medium": 6, "hard": 8}
MAX_MEMORY_MOVES = 500


def generate_memory(rng: Random, difficulty: str) -> dict:
    pairs = MEMORY_PAIRS[difficulty]
    faces = rng.sample(MEMORY_FACES, pairs)
    deck = rng.sample(faces * 2, pairs * 2)
    cards = [{"id": f"c{i + 1}", "face": face} for i, face in enumerate(deck)]
    return {"kind": "memory", "pairs": pairs, "cards": cards}


@dataclass(frozen=True)
class MemoryReplay:
    valid: bool
    moves: int = 0
    matched_pairs: int = 0


def replay_memory(cards: list[dict], moves: Any) -> MemoryReplay:
    """
    Plays the client's move log against the real board. The score comes from this replay, so a
    client can't just claim "I found all the pairs" without actually producing a solving sequence.
    `moves` is untrusted input and may have any shape.
    """
    if not isinstance(moves, list) or len(moves) > MAX_MEMORY_MOVES:
        return MemoryReplay(valid=False)

    face_of = {card["id"]: card["face"] for card in cards}
    matched: set[str] = set()
    for move in moves:
        if not isinstance(move, list) or len(move) != 2:
            return MemoryReplay(valid=False)
        first, second = move
        if not (isinstance(first, str) and isinstance(second, str)):
            return MemoryReplay(valid=False)
        if first == second or first not in face_of or second not in face_of:
            return MemoryReplay(valid=False)
        if first in matched or second in matched:
            return MemoryReplay(valid=False)
        if face_of[first] == face_of[second]:
            matched.update((first, second))

    matched_pairs = len(matched) // 2
    return MemoryReplay(
        valid=matched_pairs == len(cards) // 2, moves=len(moves), matched_pairs=matched_pairs
    )


# ============================================================================ shared quiz helpers


def _with_options(rng: Random, question_id: str, answer: dict, distractors: list[dict]) -> dict:
    shuffled = rng.sample([answer, *distractors[:3]], len(distractors[:3]) + 1)
    options = [{"id": f"{question_id}_o{i + 1}", **item} for i, item in enumerate(shuffled)]
    return {"options": options, "correct_option_id": options[shuffled.index(answer)]["id"]}


# ============================================================================ missing number

SEQUENCE_LENGTH = 5


@dataclass(frozen=True)
class NumberSequence:
    terms: list[int]
    hideable: list[int]  # never index 0: the rule must always stay visible
    rule: str
    calc: Callable[[int], str]  # the concrete calculation that produces the term at index i


def _build_sequence(first: int, next_term: Callable[[int, int, list[int]], int]) -> list[int]:
    terms = [first]
    for k in range(1, SEQUENCE_LENGTH):
        terms.append(next_term(terms[k - 1], k, terms))
    return terms


def _add(start_min: int, start_max: int, step_min: int, step_max: int):
    def template(rng: Random) -> NumberSequence:
        d = rng.randint(step_min, step_max)
        t = _build_sequence(rng.randint(start_min, start_max), lambda p, _k, _a: p + d)
        return NumberSequence(
            t,
            [1, 2, 3, 4],
            f"Har bir son oldingisidan {d} taga katta.",
            lambda i: f"{t[i - 1]} + {d} = {t[i]}",
        )

    return template


def _subtract(rng: Random) -> NumberSequence:
    d = rng.randint(2, 9)
    t = _build_sequence(rng.randint(50, 90), lambda p, _k, _a: p - d)
    return NumberSequence(
        t,
        [1, 2, 3, 4],
        f"Har bir son oldingisidan {d} taga kichik.",
        lambda i: f"{t[i - 1]} − {d} = {t[i]}",
    )


def _multiply(max_start: int, ratios: list[int]):
    def template(rng: Random) -> NumberSequence:
        r = rng.choice(ratios)
        t = _build_sequence(rng.randint(1, max_start), lambda p, _k, _a: p * r)
        return NumberSequence(
            t,
            [1, 2, 3, 4],
            f"Har bir son oldingisidan {r} marta katta.",
            lambda i: f"{t[i - 1]} × {r} = {t[i]}",
        )

    return template


def _growing(rng: Random) -> NumberSequence:
    d0 = rng.randint(1, 3)
    t = _build_sequence(rng.randint(1, 10), lambda p, k, _a: p + d0 + k - 1)
    return NumberSequence(
        t,
        [2, 3, 4],
        f"Qo‘shiladigan son har safar 1 taga oshadi: +{d0}, +{d0 + 1}, +{d0 + 2}…",
        lambda i: f"{t[i - 1]} + {d0 + i - 1} = {t[i]}",
    )


def _squares(rng: Random) -> NumberSequence:
    n0 = rng.randint(1, 5)
    t = _build_sequence(n0 * n0, lambda _p, k, _a: (n0 + k) * (n0 + k))
    return NumberSequence(
        t,
        [1, 2, 3, 4],
        "Bular ketma-ket sonlarning kvadratlari (sonni o‘ziga ko‘paytiramiz).",
        lambda i: f"{n0 + i} × {n0 + i} = {t[i]}",
    )


def _fibonacci(rng: Random) -> NumberSequence:
    a = rng.randint(1, 3)
    t = _build_sequence(
        a, lambda p, k, terms: rng.randint(a, a + 3) if k == 1 else p + terms[k - 2]
    )
    return NumberSequence(
        t,
        [2, 3, 4],
        "Har bir son oldingi ikkita son yig‘indisiga teng.",
        lambda i: f"{t[i - 2]} + {t[i - 1]} = {t[i]}",
    )


def _double_plus_one(rng: Random) -> NumberSequence:
    t = _build_sequence(rng.randint(1, 4), lambda p, _k, _a: p * 2 + 1)
    return NumberSequence(
        t,
        [1, 2, 3, 4],
        "Har bir sonni 2 ga ko‘paytirib, 1 qo‘shamiz.",
        lambda i: f"{t[i - 1]} × 2 + 1 = {t[i]}",
    )


NUMBER_TEMPLATES = {
    "easy": [_add(1, 20, 2, 9), _add(1, 30, 2, 5), _subtract],
    "medium": [_multiply(4, [2, 3]), _add(10, 40, 11, 25), _growing],
    "hard": [_squares, _fibonacci, _double_plus_one, _multiply(5, [3, 4])],
}


def generate_missing_number(rng: Random, difficulty: str, count: int = 8) -> dict:
    questions: list[dict] = []
    seen: set[tuple] = set()
    while len(questions) < count:
        sequence = rng.choice(NUMBER_TEMPLATES[difficulty])(rng)
        hidden = rng.choice(sequence.hideable)
        key = (*sequence.terms, hidden)
        if key in seen:
            continue
        seen.add(key)

        answer = sequence.terms[hidden]
        step = max(1, abs(answer - sequence.terms[hidden - 1]))
        near = {answer + 1, answer - 1, answer + 2, answer - 2, answer + step, answer - step}
        near.add(answer + 10)
        candidates = sorted(value for value in near if value >= 0 and value != answer)
        distractors = rng.sample(candidates, 3)

        question_id = f"mn{len(questions) + 1}"
        questions.append(
            {
                "id": question_id,
                "sequence": [None if i == hidden else v for i, v in enumerate(sequence.terms)],
                **_with_options(
                    rng, question_id, {"value": answer}, [{"value": v} for v in distractors]
                ),
                "explanation": f"{sequence.rule} {sequence.calc(hidden)}.",
            }
        )
    return {"kind": "missing-number", "questions": questions}


# ============================================================================ pattern master

PLAIN_SHAPES = ["circle", "square", "triangle", "star", "diamond", "hexagon"]
COLORS = ["teal", "yellow", "pink", "blue", "orange", "purple"]
SHAPE_NAMES = {
    "circle": "doira",
    "square": "kvadrat",
    "triangle": "uchburchak",
    "star": "yulduz",
    "diamond": "romb",
    "hexagon": "oltiburchak",
    "arrow": "strelka",
}
COLOR_NAMES = {
    "teal": "yashil",
    "yellow": "sariq",
    "pink": "pushti",
    "blue": "ko‘k",
    "orange": "to‘q sariq",
    "purple": "binafsha",
}
DIRECTION_NAMES = {0: "o‘ngga", 90: "pastga", 180: "chapga", 270: "yuqoriga"}

# Repeating motifs; numbers index into the values chosen for a rule.
MOTIFS = {"AB": [0, 1], "ABC": [0, 1, 2], "AAB": [0, 0, 1], "ABB": [0, 1, 1]}
MOTIF_NAMES = list(MOTIFS)
VISIBLE_ITEMS = 6  # item 7 is the answer, so every rule repeats at least twice
MAX_GENERATION_TRIES = 200


@dataclass(frozen=True)
class AttributeRule:
    at: Callable[[int], Any]  # the attribute's value at position i
    explain: str
    alternatives: list  # plausible wrong values


def _cycle(rng: Random, pool: list, motif: str, name: Callable, label: str) -> AttributeRule:
    size = max(MOTIFS[motif]) + 1
    values = rng.sample(pool, size)
    order = [values[k] for k in MOTIFS[motif]]
    leftovers = [value for value in pool if value not in values]
    arrow_text = " → ".join(name(value) for value in order)
    return AttributeRule(
        at=lambda i: order[i % len(order)],
        explain=f"{label}: {arrow_text}, keyin yana boshidan.",
        alternatives=[*values, *rng.sample(leftovers, min(1, len(leftovers)))],
    )


def _fixed(value: Any, alternatives: list) -> AttributeRule:
    return AttributeRule(at=lambda _i: value, explain="", alternatives=alternatives)


def _rotation_rule(rng: Random) -> AttributeRule:
    start = rng.choice([0, 90, 180, 270])
    return AttributeRule(
        at=lambda i: (start + i * 90) % 360,
        explain="Strelka har safar soat mili bo‘yicha chorak aylanadi.",
        alternatives=[0, 90, 180, 270],
    )


def _pattern_plan(rng: Random, difficulty: str) -> dict[str, AttributeRule]:
    def shapes(motif):
        return _cycle(rng, PLAIN_SHAPES, motif, SHAPE_NAMES.get, "Shakllar tartibi")

    def colors(motif):
        return _cycle(rng, COLORS, motif, COLOR_NAMES.get, "Ranglar tartibi")

    def counts(motif):
        return _cycle(rng, [1, 2, 3], motif, str, "Shakllar soni")

    def one_shape():
        return _fixed(rng.choice(PLAIN_SHAPES), PLAIN_SHAPES)

    def one_color():
        return _fixed(rng.choice(COLORS), COLORS)

    no_rotation = _fixed(0, [0])
    single = _fixed(1, [1, 2])
    arrow = _fixed("arrow", ["arrow"])

    if difficulty == "easy":
        if rng.random() < 0.5:
            type_rule, color_rule = shapes(rng.choice(MOTIF_NAMES)), one_color()
        else:
            type_rule, color_rule = one_shape(), colors(rng.choice(MOTIF_NAMES))
        return {"type": type_rule, "color": color_rule, "rotation": no_rotation, "count": single}

    variant = rng.randint(0, 2)
    if difficulty == "medium":
        if variant == 0:
            return {
                "type": shapes("AB"),
                "color": colors("ABC"),
                "rotation": no_rotation,
                "count": single,
            }
        if variant == 1:
            return {
                "type": arrow,
                "color": colors("AB"),
                "rotation": _rotation_rule(rng),
                "count": single,
            }
        return {
            "type": shapes("ABC"),
            "color": one_color(),
            "rotation": no_rotation,
            "count": counts("AB"),
        }

    if variant == 0:
        return {
            "type": shapes("ABC"),
            "color": colors("AB"),
            "rotation": no_rotation,
            "count": counts("ABC"),
        }
    if variant == 1:
        return {
            "type": arrow,
            "color": colors("ABC"),
            "rotation": _rotation_rule(rng),
            "count": counts("AB"),
        }
    return {
        "type": shapes("AAB"),
        "color": colors("ABC"),
        "rotation": no_rotation,
        "count": counts("AB"),
    }


def _shape_key(shape: dict) -> tuple:
    return (shape["type"], shape["color"], shape["rotation"], shape["count"])


def describe_shape(shape: dict) -> str:
    count = f"{shape['count']} ta " if shape["count"] > 1 else ""
    base = f"{count}{COLOR_NAMES[shape['color']]} {SHAPE_NAMES[shape['type']]}"
    if shape["type"] == "arrow":
        return f"{base} ({DIRECTION_NAMES.get(shape['rotation'], '')})"
    return base


def generate_pattern(rng: Random, difficulty: str, count: int = 6) -> dict:
    questions: list[dict] = []
    seen: set[tuple] = set()
    tries = 0
    while len(questions) < count and tries < MAX_GENERATION_TRIES:
        tries += 1
        plan = _pattern_plan(rng, difficulty)
        items = [
            {attribute: rule.at(i) for attribute, rule in plan.items()}
            for i in range(VISIBLE_ITEMS + 1)
        ]
        answer = items[VISIBLE_ITEMS]
        key = tuple(_shape_key(item) for item in items)
        if key in seen:
            continue
        seen.add(key)

        # Each wrong option differs from the answer in one attribute, so it's "almost right".
        candidates = [
            {**answer, attribute: value}
            for attribute, rule in plan.items()
            for value in rule.alternatives
        ]
        unique = {_shape_key(c): c for c in candidates if _shape_key(c) != _shape_key(answer)}
        if len(unique) < 3:
            continue
        distractors = rng.sample(list(unique.values()), 3)

        question_id = f"pt{len(questions) + 1}"
        rules = [plan[name].explain for name in ("type", "color", "count", "rotation")]
        explanation = " ".join(rule for rule in rules if rule)
        questions.append(
            {
                "id": question_id,
                "sequence": [*items[:VISIBLE_ITEMS], None],
                **_with_options(
                    rng, question_id, {"shape": answer}, [{"shape": s} for s in distractors]
                ),
                "explanation": f"{explanation} Demak, keyingisi — {describe_shape(answer)}.",
            }
        )
    return {"kind": "pattern", "questions": questions}


# ============================================================================ registry

# A game kind is playable only once it has a generator here (and an engine in the frontend).
GENERATORS: dict[str, Callable[[Random, str], dict]] = {
    "memory": generate_memory,
    "missing-number": generate_missing_number,
    "pattern": generate_pattern,
}
