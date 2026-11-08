from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Pupil
from apps.exams.importer import import_exam_data
from apps.exams.models import ExamAttempt, ExamTarget, Question
from apps.schools.models import Classroom, District, Region, School

ALIYA_JSHSHIR = "11111111111111"
BEK_JSHSHIR = "22222222222222"


def text(value: str) -> str:
    return f"<p>{value}</p>"


def make_region() -> Region:
    region, _ = Region.objects.get_or_create(number=1, defaults={"name": "Viloyat"})
    return region


def make_classroom(school_number: int = 1, number: int = 5, category: str = "A") -> Classroom:
    region = make_region()
    district, _ = District.objects.get_or_create(
        region=region, number=1, defaults={"name": "Tuman"}
    )
    school, _ = School.objects.get_or_create(
        district=district, number=school_number, defaults={"name": f"{school_number}-maktab"}
    )
    classroom, _ = Classroom.objects.get_or_create(school=school, number=number, category=category)
    return classroom


def make_pupil(jshshir: str, first_name: str) -> Pupil:
    pupil = Pupil(classroom=make_classroom(), first_name=first_name, last_name="Test")
    pupil.set_imie(jshshir)
    pupil.save()
    return pupil


def make_exam(targets=None, **overrides):
    """
    Three subjects with two questions each, so percentages are easy to check by eye.
    By default the exam is assigned to the region every test pupil lives in; pass `targets`
    (a list of ExamTarget field dicts, possibly empty) to test assignment itself.
    """
    questions = []
    for number, subject in enumerate(["math", "math", "iq", "iq", "language", "language"], start=1):
        questions.append(
            {
                "number": number,
                "subject": subject,
                "prompt": text(f"Savol {number}"),
                "explanation": text(f"Izoh {number}"),
                "options": [
                    {"label": "A", "content": text("to‘g‘ri"), "isCorrect": True},
                    {"label": "B", "content": text("noto‘g‘ri")},
                ],
            }
        )
    data = {
        "title": "Test imtihon",
        "durationMinutes": 60,
        "sections": [
            {"subject": "math", "title": "Matematika"},
            {"subject": "iq", "title": "Mantiq"},
            {"subject": "language", "title": "Ona tili"},
        ],
        "questions": questions,
        **overrides,
    }
    exam = import_exam_data(data, publish=True)
    for target in [{"region": make_region()}] if targets is None else targets:
        ExamTarget.objects.create(exam=exam, **target)
    return exam


def client_for(pupil: Pupil | None = None) -> APIClient:
    """A client that behaves like the frontend: it always sends the X-Requested-With header."""
    client = APIClient(HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    if pupil is not None:
        session = client.session
        session["pupil_id"] = str(pupil.pk)
        session.save()
    return client


def options_of(question: Question) -> tuple[str, str]:
    """Returns (correct option id, wrong option id)."""
    options = list(question.options.all())
    right = next(option for option in options if option.is_correct)
    wrong = next(option for option in options if not option.is_correct)
    return str(right.pk), str(wrong.pk)


def expire(attempt: ExamAttempt, seconds_past_deadline: int) -> None:
    """Moves the attempt's deadline into the past, instead of a test actually waiting for it."""
    deadline = timezone.now() - timedelta(seconds=seconds_past_deadline)
    ExamAttempt.objects.filter(pk=attempt.pk).update(
        started_at=deadline - timedelta(hours=1), expires_at=deadline
    )
    attempt.refresh_from_db()


@pytest.fixture(autouse=True)
def clear_throttle_counters():
    cache.clear()


@pytest.fixture
def aliya(db) -> Pupil:
    return make_pupil(ALIYA_JSHSHIR, "Aliya")


@pytest.fixture
def bek(db) -> Pupil:
    return make_pupil(BEK_JSHSHIR, "Bek")


@pytest.fixture
def exam(db):
    return make_exam()


@pytest.fixture
def api(aliya) -> APIClient:
    return client_for(aliya)
