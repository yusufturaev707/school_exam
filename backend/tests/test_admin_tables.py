"""Every table in the database is in the admin sidebar, and every list and detail page opens."""

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.sessions.models import Session
from django.urls import reverse

from apps.exams.models import AnswerOption, AttemptAnswer, ExamAttempt
from apps.exams.services import start_attempt

from .conftest import ALIYA_JSHSHIR, client_for, make_exam, make_pupil

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff(client):
    user = get_user_model().objects.create_superuser("admin", password="pass-for-tests")
    client.force_login(user)
    return client


@pytest.fixture
def data(db):
    """At least one row in the tables the exam fills, so detail pages can be opened too."""
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


def test_every_model_is_registered():
    missing = [m._meta.label for m in apps.get_models() if not admin.site.is_registered(m)]
    assert missing == []


@pytest.mark.parametrize("model", apps.get_models(), ids=lambda m: m._meta.label)
def test_list_and_first_record_open(staff, data, model):
    opts = model._meta
    response = staff.get(reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist"))
    assert response.status_code == 200
    first = model._default_manager.first()
    if first is not None:
        url = reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[first.pk])
        assert staff.get(url).status_code == 200


def test_sidebar_lists_the_new_tables(staff, data):
    page = staff.get("/admin/").content.decode()
    for name in [
        "Javob variantlari",
        "O‘quvchi javoblari",
        "Bo‘limlar",
        "Kun savollariga javoblar",
    ]:
        assert name in page


def test_pupil_answer_shows_the_chosen_letter(staff, data):
    page = staff.get(reverse("admin:exams_attemptanswer_changelist")).content.decode()
    assert '<td class="field-chosen">A</td>' in page


def test_option_cannot_be_edited_alone(staff, data):
    option = AnswerOption.objects.first()
    page = staff.get(reverse("admin:exams_answeroption_change", args=[option.pk])).content.decode()
    assert 'name="is_correct"' not in page


class TestSessions:
    def test_superuser_sees_whose_session_it_is_but_not_its_data(self, staff, data):
        client_for(data.pupil)  # logs the pupil in: a second session
        page = staff.get(reverse("admin:sessions_session_changelist")).content.decode()
        assert "Xodim: admin" in page and "O‘quvchi: Test Aliya" in page
        for session in Session.objects.all():
            assert session.session_data not in page

    def test_deleting_a_session_logs_that_browser_out(self, staff, data):
        pupil_client = client_for(data.pupil)
        assert pupil_client.get("/api/auth/me").status_code == 200
        pupil_session = Session.objects.get(
            session_key=pupil_client.cookies[settings.SESSION_COOKIE_NAME].value
        )
        staff.post(
            reverse("admin:sessions_session_changelist"),
            {"action": "delete_selected", "_selected_action": [pupil_session.pk], "post": "yes"},
        )
        assert pupil_client.get("/api/auth/me").status_code in (401, 403)

    def test_staff_with_every_permission_but_not_superuser(self, client, data):
        user = get_user_model().objects.create_user("operator", password="x", is_staff=True)
        user.user_permissions.add(*Permission.objects.all())
        client.force_login(user)
        assert client.get(reverse("admin:sessions_session_changelist")).status_code == 403
        assert "Sessiyalar" not in client.get("/admin/").content.decode()


def test_attempt_records_stay_read_only(staff, data):
    url = reverse("admin:exams_attemptanswer_change", args=[data.answers.first().pk])
    assert staff.post(url, {}).status_code == 403
    assert ExamAttempt.objects.count() == 1
