"""
An exam as one JSON file: loaded by `import_exam` and by "JSON fayldan yuklash" in the admin,
written by "JSON yuklab olish" on an exam's admin page. Handy for a question bank prepared in
advance, and for copying an exam from one server to another.

Texts (`prompt`, `passage`, `explanation`, option `content`) are the same HTML the admin editor
produces, with formulas between $ signs and pictures inside as data URIs.
Format example: apps/demo/data/exam.json

Optional keys: `shuffleQuestions` and `shuffleOptions` (exam), `difficulty` (question: 1 oson,
2 o‘rta, 3 qiyin), and `grades`, a list of grade numbers the exam is assigned to (e.g. [4]: every
4th grade). Narrower targets (a district, a school) are chosen in the admin: their ids differ
from one server to another, so they are not part of the file.
"""

from django.core.exceptions import NON_FIELD_ERRORS, FieldDoesNotExist, ValidationError
from django.db import transaction
from django.utils.text import capfirst

from .models import AnswerOption, Exam, ExamSection, ExamTarget, Question


@transaction.atomic
def import_exams_data(data, publish: bool = False, skip_titles=()) -> tuple[list[Exam], list[str]]:
    """
    A file holds one exam ({…}) or several ([{…}, {…}], as `export_exams` writes). All or
    nothing over the whole file. Exams whose title is in `skip_titles` are left out, so loading
    the same file twice doesn't make copies. Returns (created exams, skipped titles).
    """
    items = data if isinstance(data, list) else [data]
    if not items:
        raise ValueError("Faylda imtihon yo‘q.")
    created, skipped = [], []
    for position, item in enumerate(items, start=1):
        title = item.get("title") if isinstance(item, dict) else None
        if title in skip_titles:
            skipped.append(title)
            continue
        try:
            created.append(import_exam_data(item, publish=publish))
        except ValueError as error:
            if len(items) == 1:
                raise
            raise ValueError(f"“{title or position}” imtihoni: {error}") from error
    return created, skipped


@transaction.atomic
def import_exam_data(data: dict, publish: bool = False) -> Exam:
    """All or nothing: raises ValueError saying what and where is wrong, and then saves nothing."""
    if not isinstance(data, dict):
        raise ValueError("Fayl tuzilishi noto‘g‘ri: ichida bitta imtihon ({…}) bo‘lsin.")
    exam = _saved(
        "Imtihon",
        lambda: Exam(
            title=data["title"],
            description=data.get("description", ""),
            duration_minutes=data["durationMinutes"],
            points_per_question=data.get("pointsPerQuestion", 2),
            review_enabled=data.get("reviewEnabled", True),
            shuffle_questions=data.get("shuffleQuestions", False),
            shuffle_options=data.get("shuffleOptions", False),
            is_published=publish,
        ),
    )
    for grade in _list(data, "grades", required=False):
        _saved("“grades”", lambda grade=grade: ExamTarget(exam=exam, grade=grade))
    for order, section in enumerate(_list(data, "sections"), start=1):
        _saved(
            f"{order}-bo‘lim",
            lambda section=section, order=order: ExamSection(
                exam=exam, subject=section["subject"], title=section["title"], order=order - 1
            ),
        )
    for index, item in enumerate(_list(data, "questions"), start=1):
        _import_question(exam, item, index)
    return exam


def _import_question(exam: Exam, item: dict, index: int) -> None:
    number = item.get("number", index) if isinstance(item, dict) else index
    # The position in the list too, when it differs: with a repeated number, "1-savol" is ambiguous.
    where = f"{number}-savol" if number == index else f"{index}-o‘rindagi savol (raqami {number})"
    options = _list(item, "options", where=where)
    if sum(1 for option in options if isinstance(option, dict) and option.get("isCorrect")) != 1:
        raise ValueError(f'{where}: aynan bitta variantda "isCorrect": true bo‘lsin.')

    question = _saved(
        where,
        lambda: Question(
            exam=exam,
            number=item["number"],
            subject=item["subject"],
            type=item.get("type", "single_choice"),
            difficulty=item.get("difficulty"),
            prompt=item["prompt"],
            passage=item.get("passage") or "",
            explanation=item.get("explanation") or "",
        ),
    )
    for option in options:
        label = option.get("label", "?") if isinstance(option, dict) else "?"
        _saved(
            f"{where}, “{label}” varianti",
            lambda option=option: AnswerOption(
                question=question,
                label=option["label"],
                content=option["content"],
                is_correct=bool(option.get("isCorrect")),
            ),
        )


def _list(data, key: str, required: bool = True, where: str = "Imtihon") -> list:
    if not isinstance(data, dict):
        raise ValueError(f"{where}: fayl tuzilishi noto‘g‘ri.")
    if key not in data:
        if required:
            raise ValueError(f"{where}: “{key}” maydoni yo‘q.")
        return []
    if not isinstance(data[key], list):
        raise ValueError(f"{where}: “{key}” ro‘yxat ([…]) bo‘lsin.")
    return data[key]


def _saved(where: str, build):
    """Builds, validates and saves one record; any problem becomes a ValueError naming `where`."""
    try:
        instance = build()
        # Plain .save() skips model validators, and this data comes from a hand-edited file.
        instance.full_clean()
    except KeyError as error:
        raise ValueError(f"{where}: “{error.args[0]}” maydoni yo‘q.") from error
    except (TypeError, AttributeError) as error:
        raise ValueError(f"{where}: fayl tuzilishi noto‘g‘ri.") from error
    except ValidationError as error:
        raise ValueError(f"{where}: {_describe(instance, error)}") from error
    instance.save()
    return instance


def _describe(instance, error: ValidationError) -> str:
    if not hasattr(error, "error_dict"):
        return " ".join(error.messages)
    parts = []
    for field, messages in error.message_dict.items():
        if field == NON_FIELD_ERRORS:
            parts += messages
            continue
        try:
            name = capfirst(instance._meta.get_field(field).verbose_name)
        except FieldDoesNotExist:
            name = field
        parts += [f"{name}: {message}" for message in messages]
    return " ".join(parts)


def export_exam_data(exam: Exam) -> dict:
    """The exam in the format `import_exam_data` reads, so the file can be loaded again."""
    questions = exam.questions.prefetch_related("options").order_by("number")
    return {
        "title": exam.title,
        "description": exam.description,
        "durationMinutes": exam.duration_minutes,
        "pointsPerQuestion": exam.points_per_question,
        "reviewEnabled": exam.review_enabled,
        "shuffleQuestions": exam.shuffle_questions,
        "shuffleOptions": exam.shuffle_options,
        "grades": sorted(
            target.grade
            for target in exam.targets.all()
            if target.grade is not None
            and not any(getattr(target, f"{place}_id") for place in ExamTarget.PLACES)
        ),
        "sections": [
            {"subject": section.subject, "title": section.title} for section in exam.sections.all()
        ],
        "questions": [
            {
                "number": question.number,
                "subject": question.subject,
                "type": question.type,
                "difficulty": question.difficulty,
                "prompt": question.prompt,
                "passage": question.passage,
                "explanation": question.explanation,
                "options": [
                    {"label": o.label, "content": o.content, "isCorrect": o.is_correct}
                    for o in question.options.all()
                ],
            }
            for question in questions
        ],
    }
