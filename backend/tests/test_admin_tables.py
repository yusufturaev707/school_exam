"""The admin sidebar: which tables are in it, and that every page in it opens."""

import pytest
from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.exams.models import AnswerOption, AttemptAnswer
from apps.exams.services import start_attempt

from .conftest import ALIYA_JSHSHIR, make_exam, make_pupil

pytestmark = pytest.mark.django_db

# Left out on purpose: edited on another page (exam: Kimga, Bo‘limlar; question: Javob variantlari;
# attempt: the answer key), or internal to Django and the games.
HIDDEN = {
    "contenttypes.ContentType",
    "auth.Permission",
    "sessions.Session",
    "exams.ExamTarget",
    "exams.ExamSection",
    "exams.AnswerOption",
    "exams.AttemptAnswer",
    "games.DailyChallengeCompletion",
    "games.DailyQuestionAnswer",
}
REGISTERED = [m for m in apps.get_models() if admin.site.is_registered(m)]


@pytest.fixture
def staff(client):
    user = get_user_model().objects.create_superuser("admin", password="pass-for-tests")
    client.force_login(user)
    return client


@pytest.fixture
def data(db):
    """A row in the tables the exam fills, so detail pages can be opened too."""
    exam = make_exam()
    pupil = make_pupil(ALIYA_JSHSHIR, "Aliya")
    attempt, _ = start_attempt(pupil, exam.pk)
    option = AnswerOption.objects.filter(question__exam=exam).first()
    AttemptAnswer.objects.create(
        attempt=attempt,
        question=option.question,
        selected_option_ids=[str(option.pk)],
        client_seq=1,
    )
    return attempt


def test_sidebar_has_every_table_except_the_hidden_ones():
    shown = {m._meta.label for m in REGISTERED}
    every = {m._meta.label for m in apps.get_models()}
    assert shown == every - HIDDEN


def test_sidebar_does_not_list_the_hidden_ones(staff, data):
    page = staff.get("/admin/").content.decode()
    for url in [
        "contenttypes/contenttype",
        "exams/answeroption",
        "exams/examtarget",
        "auth/permission",
    ]:
        assert f"/admin/{url}/" not in page
    assert "/admin/admin/logentry/" in page


@pytest.mark.parametrize("model", REGISTERED, ids=lambda m: m._meta.label)
def test_list_and_first_record_open(staff, data, model):
    opts = model._meta
    response = staff.get(reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist"))
    assert response.status_code == 200
    first = model._default_manager.first()
    if first is not None:
        url = reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[first.pk])
        assert staff.get(url).status_code == 200


def test_admin_history_is_read_only(staff):
    assert staff.get("/admin/admin/logentry/add/").status_code == 403
