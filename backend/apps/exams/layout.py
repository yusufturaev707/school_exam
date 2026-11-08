"""
Every pupil gets the same questions, but, when the exam asks for it, in their own order and with
their own option order. A neighbour's screen then doesn't help: question 3 is a different question,
and where it is the same one, its answer is under a different letter.

The order is drawn once, when the attempt starts, and stored on the attempt (`ExamAttempt.layout`).
Everything a pupil or an admin sees about that attempt is arranged from it: the questions during
the exam, the review after it, and the answer key in the admin. Scoring doesn't need it at all,
because answers are stored as option ids, never as letters.

Questions are shuffled inside each subject section (the frontend shows a section as one block),
and inside a section only among questions of the same difficulty, so every pupil still goes from
easy to hard.
"""

import secrets
from dataclasses import dataclass
from itertools import groupby
from uuid import UUID

from .models import AnswerOption, Exam, Question

LABELS = "ABCDEFGHIJ"

_random = secrets.SystemRandom()  # nobody can predict another pupil's order from their own


@dataclass(frozen=True)
class ShownOption:
    id: UUID
    label: str
    content: str
    is_correct: bool


@dataclass(frozen=True)
class ShownQuestion:
    """A question as one pupil sees it: their position number and their option letters."""

    id: UUID
    number: int
    original_number: int
    subject: str
    type: str
    difficulty: int | None
    prompt: str
    passage: str
    explanation: str
    options: list[ShownOption]


def draw_layout(exam: Exam, questions: list[Question]) -> dict:
    """A fresh random order for one attempt, or {} when the exam doesn't shuffle."""
    layout: dict = {}
    if exam.shuffle_questions:
        ordered = sorted(questions, key=_canonical_key(exam))
        order: list[Question] = []
        for _, group in groupby(ordered, key=_group_key(exam)):
            group = list(group)
            _random.shuffle(group)
            order.extend(group)
        layout["questions"] = [str(question.pk) for question in order]
    if exam.shuffle_options:
        layout["options"] = {}
        for question in questions:
            ids = [str(option.pk) for option in question.options.all()]
            _random.shuffle(ids)
            layout["options"][str(question.pk)] = ids
    return layout


def arrange(exam: Exam, layout: dict, questions: list[Question]) -> list[ShownQuestion]:
    """
    Puts `questions` (with prefetched options) in the attempt's order and letters them.
    A question or option added after the attempt started comes after the ones in the layout,
    and one deleted since is simply missing, so editing an exam never breaks a running attempt.
    """
    question_order = {qid: i for i, qid in enumerate(layout.get("questions", []))}
    option_orders = layout.get("options", {})
    if question_order:
        section = _section_rank(exam)
        unknown = len(question_order)
        questions = sorted(
            questions,
            key=lambda q: (
                section(q.subject),
                question_order.get(str(q.pk), unknown),
                q.number,
            ),
        )
    else:
        questions = sorted(questions, key=lambda q: q.number)

    shown = []
    for position, question in enumerate(questions, start=1):
        option_order = option_orders.get(str(question.pk))
        shown.append(
            ShownQuestion(
                id=question.pk,
                number=position if question_order else question.number,
                original_number=question.number,
                subject=question.subject,
                type=question.type,
                difficulty=question.difficulty,
                prompt=question.prompt,
                passage=question.passage,
                explanation=question.explanation,
                options=_arrange_options(list(question.options.all()), option_order),
            )
        )
    return shown


def _arrange_options(options: list[AnswerOption], order: list[str] | None) -> list[ShownOption]:
    if order is None:
        return [ShownOption(o.pk, o.label, o.content, o.is_correct) for o in options]
    rank = {oid: i for i, oid in enumerate(order)}
    options = sorted(options, key=lambda o: (rank.get(str(o.pk), len(rank)), o.label))
    return [
        ShownOption(o.pk, LABELS[i] if i < len(LABELS) else o.label, o.content, o.is_correct)
        for i, o in enumerate(options)
    ]


def _section_rank(exam: Exam):
    ranks = {section.subject: i for i, section in enumerate(exam.sections.all())}
    return lambda subject: ranks.get(subject, len(ranks))


def _canonical_key(exam: Exam):
    section = _section_rank(exam)
    return lambda q: (section(q.subject), q.difficulty or 0, q.number)


def _group_key(exam: Exam):
    section = _section_rank(exam)
    return lambda q: (section(q.subject), q.difficulty or 0)
