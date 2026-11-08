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

from dataclasses import dataclass, field

from django.core.exceptions import NON_FIELD_ERRORS, FieldDoesNotExist, ValidationError
from django.db import transaction
from django.utils.text import capfirst

from .models import AnswerOption, Exam, ExamSection, ExamTarget, Question


@dataclass
class Outcome:
    title: str
    action: str  # "created", "updated" or "skipped"
    exam: Exam | None = None
    counts: dict[str, int] = field(default_factory=dict)  # questions, for "updated"


@transaction.atomic
def import_exams_data(data, publish: bool = False, on_existing: str = "copy") -> list[Outcome]:
    """
    A file holds one exam ({…}) or several ([{…}, {…}], as `export_exams` writes). All or
    nothing over the whole file. When an exam with the same title is already in the database,
    `on_existing` says what to do: "copy" creates another one, "skip" leaves it alone (so loading
    a file twice makes no copies), "update" brings it in line with the file (update_exam_data).
    """
    items = data if isinstance(data, list) else [data]
    if not items:
        raise ValueError("Faylda imtihon yo‘q.")
    outcomes = []
    for position, item in enumerate(items, start=1):
        title = item.get("title") if isinstance(item, dict) else None
        same = list(Exam.objects.filter(title=title)) if title and on_existing != "copy" else []
        try:
            if not same:
                exam = import_exam_data(item, publish=publish)
                outcomes.append(Outcome(title, "created", exam))
            elif on_existing == "skip":
                outcomes.append(Outcome(title, "skipped"))
            elif len(same) > 1:
                raise ValueError(
                    f"bazada shu nomli {len(same)} ta imtihon bor, qaysi birini yangilash "
                    "noma’lum. Ortiqchasining nomini admin'da o‘zgartiring."
                )
            else:
                counts = update_exam_data(same[0], item, publish=publish)
                outcomes.append(Outcome(title, "updated", same[0], counts))
        except ValueError as error:
            if len(items) == 1:
                raise
            raise ValueError(f"“{title or position}” imtihoni: {error}") from error
    return outcomes


@transaction.atomic
def update_exam_data(exam: Exam, data: dict, publish: bool = False) -> dict[str, int]:
    """
    Brings an existing exam in line with the file: its settings, sections and questions (by
    number) with their options (by letter). Records are changed in place and keep their ids, so
    pupils' answers, orders and results stay valid. If pupils have taken the exam, a question or
    an option that is missing from the file can't be deleted: then nothing is saved.
    `publish` publishes the exam; otherwise its published state is left as it is. Targets
    ("Kimga") are only added for new `grades`: places chosen in the admin are kept.
    Returns how many questions were added, changed, left unchanged and removed.
    """
    if not isinstance(data, dict):
        raise ValueError("Fayl tuzilishi noto‘g‘ri: ichida bitta imtihon ({…}) bo‘lsin.")
    taken = exam.attempts.exists()

    def settings():
        exam.title = data["title"]
        exam.description = data.get("description", "")
        exam.duration_minutes = data["durationMinutes"]
        exam.points_per_question = data.get("pointsPerQuestion", 2)
        exam.review_enabled = data.get("reviewEnabled", True)
        exam.shuffle_questions = data.get("shuffleQuestions", False)
        exam.shuffle_options = data.get("shuffleOptions", False)
        exam.is_published = exam.is_published or publish
        return exam

    _saved("Imtihon", settings)

    grade_only = {name: None for name in ExamTarget.PLACES}
    have = set(exam.targets.filter(**grade_only).values_list("grade", flat=True))
    for grade in _list(data, "grades", required=False):
        if grade not in have:
            _saved("“grades”", lambda grade=grade: ExamTarget(exam=exam, grade=grade))
            have.add(grade)

    sections = {section.subject: section for section in exam.sections.all()}
    subjects = set()
    for order, item in enumerate(_list(data, "sections"), start=1):

        def section(item=item, order=order):
            found = sections.get(item["subject"]) or ExamSection(exam=exam, subject=item["subject"])
            found.title, found.order = item["title"], order - 1
            return found

        subjects.add(_saved(f"{order}-bo‘lim", section).subject)

    counts = {"added": 0, "changed": 0, "unchanged": 0, "removed": 0}
    existing = {question.number: question for question in exam.questions.all()}
    seen: set = set()
    for index, item in enumerate(_list(data, "questions"), start=1):
        number = item.get("number") if isinstance(item, dict) else None
        if number in seen:
            raise ValueError(f"{index}-o‘rindagi savol: {number} raqami faylda takrorlangan.")
        seen.add(number)
        counts[_sync_question(exam, existing.get(number), item, index, taken)] += 1

    stale = [question for number, question in existing.items() if number not in seen]
    if stale and taken:
        numbers = ", ".join(str(question.number) for question in stale)
        raise ValueError(
            f"Bu imtihonni o‘quvchilar ishlagan, shuning uchun faylda yo‘q savollarni o‘chirib "
            f"bo‘lmaydi: {numbers}. Ularni faylga qaytaring."
        )
    for question in stale:
        question.delete()
        counts["removed"] += 1

    for subject, section in sections.items():
        if subject not in subjects and not exam.questions.filter(subject=subject).exists():
            section.delete()
    return counts


def _sync_question(exam: Exam, question, item, index: int, taken: bool) -> str:
    number = item.get("number", index) if isinstance(item, dict) else index
    where = f"{number}-savol" if number == index else f"{index}-o‘rindagi savol (raqami {number})"
    options = _list(item, "options", where=where)
    if sum(1 for option in options if isinstance(option, dict) and option.get("isCorrect")) != 1:
        raise ValueError(f'{where}: aynan bitta variantda "isCorrect": true bo‘lsin.')
    before = None if question is None else _question_data(question)

    def fill():
        found = question or Question(exam=exam)
        found.number = item["number"]
        found.subject = item["subject"]
        found.type = item.get("type", "single_choice")
        found.difficulty = item.get("difficulty")
        found.prompt = item["prompt"]
        found.passage = item.get("passage") or ""
        found.explanation = item.get("explanation") or ""
        return found

    saved = _saved(where, fill)
    current = {option.label: option for option in AnswerOption.objects.filter(question=saved)}
    labels = set()
    for option in options:
        label = option.get("label", "?") if isinstance(option, dict) else "?"

        def fill_option(option=option):
            found = current.get(option["label"]) or AnswerOption(
                question=saved, label=option["label"]
            )
            found.content = option["content"]
            found.is_correct = bool(option.get("isCorrect"))
            return found

        labels.add(_saved(f"{where}, “{label}” varianti", fill_option).label)

    removed = [option for label, option in current.items() if label not in labels]
    if removed and taken:
        letters = ", ".join(sorted(option.label for option in removed))
        raise ValueError(
            f"{where}: bu imtihonni o‘quvchilar ishlagan, shuning uchun variantni o‘chirib "
            f"bo‘lmaydi: {letters}."
        )
    for option in removed:
        option.delete()

    if before is None:
        return "added"
    return "unchanged" if _question_data(saved) == before else "changed"


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
    for name, messages in error.message_dict.items():
        if name == NON_FIELD_ERRORS:
            parts += messages
            continue
        try:
            label = capfirst(instance._meta.get_field(name).verbose_name)
        except FieldDoesNotExist:
            label = name
        parts += [f"{label}: {message}" for message in messages]
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
        "questions": [_question_data(question, question.options.all()) for question in questions],
    }


def _question_data(question, options=None) -> dict:
    if options is None:  # straight from the database, not from a prefetched cache
        options = AnswerOption.objects.filter(question=question).order_by("label")
    return {
        "number": question.number,
        "subject": question.subject,
        "type": question.type,
        "difficulty": question.difficulty,
        "prompt": question.prompt,
        "passage": question.passage,
        "explanation": question.explanation,
        "options": [
            {"label": o.label, "content": o.content, "isCorrect": o.is_correct} for o in options
        ],
    }
