"""
Loads exam content from a JSON file, which is handy for a large question bank prepared in advance.
Texts (`prompt`, `passage`, `explanation`, option `content`) are the same HTML the admin editor
produces, with formulas between $ signs. Format example: apps/demo/data/exam.json
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import AnswerOption, Exam, ExamSection, Question


@transaction.atomic
def import_exam_data(data: dict, publish: bool = False) -> Exam:
    """All or nothing: raises ValueError naming the broken question, and then saves nothing."""
    try:
        exam = _saved(
            Exam(
                title=data["title"],
                description=data.get("description", ""),
                duration_minutes=data["durationMinutes"],
                points_per_question=data.get("pointsPerQuestion", 2),
                review_enabled=data.get("reviewEnabled", True),
                is_published=publish,
            )
        )
        for order, section in enumerate(data["sections"]):
            _saved(
                ExamSection(
                    exam=exam, subject=section["subject"], title=section["title"], order=order
                )
            )
        for item in data["questions"]:
            _import_question(exam, item)
    except KeyError as error:
        raise ValueError(f"Missing field: {error}") from error
    except ValidationError as error:
        raise ValueError(f"Invalid data: {error}") from error
    return exam


def _import_question(exam: Exam, item: dict) -> None:
    number = item["number"]
    if sum(1 for option in item["options"] if option.get("isCorrect")) != 1:
        raise ValueError(f"Question {number}: exactly one option must be correct.")

    try:
        question = _saved(
            Question(
                exam=exam,
                number=number,
                subject=item["subject"],
                type=item.get("type", "single_choice"),
                prompt=item["prompt"],
                passage=item.get("passage") or "",
                explanation=item.get("explanation") or "",
            )
        )
        for option in item["options"]:
            _saved(
                AnswerOption(
                    question=question,
                    label=option["label"],
                    content=option["content"],
                    is_correct=bool(option.get("isCorrect")),
                )
            )
    except ValidationError as error:
        raise ValueError(f"Question {number}: {error}") from error


def _saved(instance):
    # Plain .save() skips model validators, and this data comes from a hand-edited file.
    instance.full_clean()
    instance.save()
    return instance
