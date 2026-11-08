import csv
import io
import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.accounts.models import Pupil, QrLoginToken, hash_imie
from apps.accounts.services import authenticate_by_qr
from apps.exams.importer import import_exam_data
from apps.exams.models import Exam, ExamAttempt, ExamResult

from .conftest import client_for, expire, make_classroom, text

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff(client):
    user = get_user_model().objects.create_superuser("admin", password="pass-for-tests")
    client.force_login(user)
    return client


def pupil_form(**overrides) -> dict:
    return {
        "classroom": make_classroom().pk,
        "first_name": "Yangi",
        "last_name": "O‘quvchi",
        "middle_name": "",
        "photo_url": "",
        "status": "on",
        **overrides,
    }


class TestPupilAdmin:
    def test_every_admin_list_page_opens(self, staff, aliya):
        for path in (
            "schools/region",
            "schools/district",
            "schools/school",
            "schools/classroom",
            "accounts/pupil",
            "accounts/qrlogintoken",
            "exams/exam",
            "exams/question",
            "exams/examattempt",
            "exams/examresult",
            "games/game",
            "games/dailyquestion",
            "games/gamesession",
        ):
            assert staff.get(f"/admin/{path}/").status_code == 200, path

    def test_created_pupil_can_log_in_and_the_number_is_not_stored(self, staff):
        form = pupil_form(imie="55555555555555")
        assert staff.post("/admin/accounts/pupil/add/", form).status_code == 302

        pupil = Pupil.objects.get(first_name="Yangi")
        assert pupil.imie_hash == hash_imie("55555555555555")
        response = client_for().post(
            "/api/auth/jshshir", {"jshshir": "55555555555555"}, format="json"
        )
        assert response.status_code == 200

    def test_new_pupil_needs_a_jshshir(self, staff):
        response = staff.post("/admin/accounts/pupil/add/", pupil_form())
        assert response.status_code == 200
        assert not Pupil.objects.filter(first_name="Yangi").exists()

    def test_duplicate_jshshir_is_refused(self, staff, aliya):
        form = pupil_form(imie="11111111111111")
        assert staff.post("/admin/accounts/pupil/add/", form).status_code == 200
        assert not Pupil.objects.filter(first_name="Yangi").exists()

    def test_editing_without_jshshir_keeps_the_old_one(self, staff, aliya):
        before = aliya.imie_hash
        url = f"/admin/accounts/pupil/{aliya.pk}/change/"
        assert staff.post(url, pupil_form(first_name="Aliya2")).status_code == 302
        aliya.refresh_from_db()
        assert (aliya.first_name, aliya.imie_hash) == ("Aliya2", before)

    def test_edit_page_never_shows_the_hash(self, staff, aliya):
        page = staff.get(f"/admin/accounts/pupil/{aliya.pk}/change/").content.decode()
        assert aliya.imie_hash not in page

    def test_search_by_exact_jshshir(self, staff, aliya, bek):
        page = staff.get("/admin/accounts/pupil/", {"q": "11111111111111"}).content.decode()
        assert "Aliya" in page
        assert "Bek" not in page


class TestQrTickets:
    def post(self, client, pupils, **extra):
        data = {"action": "issue_qr_tickets", "_selected_action": [str(p.pk) for p in pupils]}
        return client.post("/admin/accounts/pupil/", {**data, **extra})

    def issue(self, client, pupils, output="print", ttl=24 * 60):
        return self.post(client, pupils, issue="yes", output=output, ttl_minutes=ttl)

    def test_first_step_asks_how_long_and_issues_nothing(self, staff, aliya):
        page = self.post(staff, [aliya]).content.decode()
        assert "1 ta chipta yaratish" in page
        assert 'name="ttl_minutes"' in page
        assert not QrLoginToken.objects.exists()

    def encoded(self, monkeypatch) -> list[str]:
        """Collects what each printed QR code holds."""
        import apps.accounts.admin as pupil_admin

        contents: list[str] = []
        real_svg = pupil_admin.qr_svg
        monkeypatch.setattr(pupil_admin, "qr_svg", lambda c: contents.append(c) or real_svg(c))
        return contents

    def test_print_page_has_a_login_link_for_each_pupil(
        self, staff, aliya, bek, monkeypatch, settings
    ):
        settings.QR_LOGIN_URL = "https://bilimdon.uz/qr"
        contents = self.encoded(monkeypatch)
        response = self.issue(staff, [aliya, bek])
        page = response.content.decode()
        assert "no-store" in response["Cache-Control"]
        assert page.count("<svg") == 2
        assert "Aliya" in page and "Bek" in page
        assert "Telefon kamerasi bilan skanerlang" in page
        # A phone camera opens the link; the token sits after "#", so no server ever receives it.
        prefix = "https://bilimdon.uz/qr#t="
        assert all(content.startswith(prefix) for content in contents)
        tokens = [content.removeprefix(prefix) for content in contents]
        assert {authenticate_by_qr(token) for token in tokens} == {aliya, bek}

    def test_without_a_login_url_the_code_holds_the_bare_token(
        self, staff, aliya, monkeypatch, settings
    ):
        settings.QR_LOGIN_URL = ""
        contents = self.encoded(monkeypatch)
        assert "QR_LOGIN_URL sozlanmagan" in self.post(staff, [aliya]).content.decode()
        self.issue(staff, [aliya])
        assert authenticate_by_qr(contents[0]) == aliya

    def test_chosen_lifetime_is_used(self, staff, aliya):
        self.issue(staff, [aliya], ttl=3 * 24 * 60)
        entry = QrLoginToken.objects.get()
        assert entry.expires_at - entry.created_at > timedelta(days=2, hours=23)

    def test_unknown_lifetime_is_rejected(self, staff, aliya):
        page = self.issue(staff, [aliya], ttl=999999).content.decode()
        assert "errorlist" in page
        assert not QrLoginToken.objects.exists()

    def test_csv_contains_working_tokens(self, staff, aliya, settings):
        settings.QR_LOGIN_URL = "https://bilimdon.uz/qr"
        response = self.issue(staff, [aliya], output="csv")
        assert response["Content-Type"].startswith("text/csv")
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        assert len(rows) == 1
        assert rows[0]["link"] == f"{settings.QR_LOGIN_URL}#t={rows[0]['token']}"
        assert authenticate_by_qr(rows[0]["token"]) == aliya
        assert QrLoginToken.objects.get().used_at is not None

    def test_pupils_who_cannot_log_in_get_no_ticket(self, staff, aliya, bek):
        Pupil.objects.filter(pk=bek.pk).update(status=False)
        assert "1 ta o‘quvchi tashlab ketiladi" in self.post(staff, [aliya, bek]).content.decode()
        self.issue(staff, [aliya, bek])
        assert list(QrLoginToken.objects.values_list("pupil", flat=True)) == [aliya.pk]

    def test_too_many_at_once_is_refused(self, staff, aliya, monkeypatch):
        monkeypatch.setattr("apps.accounts.admin.MAX_QR_TICKETS", 0)
        response = self.issue(staff, [aliya], output="csv")
        assert response.status_code == 302
        assert not QrLoginToken.objects.exists()

    def test_view_only_staff_cannot_issue(self, client, aliya):
        user = get_user_model().objects.create_user("viewer", password="x", is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename="view_pupil"))
        client.force_login(user)
        assert "issue_qr_tickets" not in client.get("/admin/accounts/pupil/").content.decode()
        self.issue(client, [aliya])
        assert not QrLoginToken.objects.exists()


class TestQuestionAdmin:
    def test_exactly_one_correct_option_is_required(self, staff, exam):
        question = exam.questions.first()
        options = list(question.options.all())
        form = {
            "exam": exam.pk,
            "number": question.number,
            "subject": question.subject,
            "type": question.type,
            "prompt": question.prompt,
            "passage": "",
            "explanation": "",
            "options-TOTAL_FORMS": 2,
            "options-INITIAL_FORMS": 2,
            "options-MIN_NUM_FORMS": 0,
            "options-MAX_NUM_FORMS": 1000,
        }
        for index, option in enumerate(options):
            form[f"options-{index}-id"] = option.pk
            form[f"options-{index}-question"] = question.pk
            form[f"options-{index}-label"] = option.label
            form[f"options-{index}-content"] = option.content
            form[f"options-{index}-is_correct"] = "on"  # both marked correct

        url = f"/admin/exams/question/{question.pk}/change/"
        response = staff.post(url, form)
        assert response.status_code == 200
        assert "bitta javob" in response.content.decode()


class TestAttemptAdmin:
    def test_results_cannot_be_edited(self, staff, api, exam):
        attempt_id = api.post(f"/api/examinations/{exam.pk}/start").json()["attemptId"]
        attempt = ExamAttempt.objects.get(pk=attempt_id)
        url = f"/admin/exams/examattempt/{attempt.pk}/change/"
        assert staff.post(url, {"status": "submitted"}).status_code == 403

    def test_deleting_an_attempt_allows_a_retake(self, staff, api, exam):
        attempt_id = api.post(f"/api/examinations/{exam.pk}/start").json()["attemptId"]
        api.post(
            f"/api/examinations/attempts/{attempt_id}/submit",
            {"reason": "manual"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="k",
        )
        assert api.post(f"/api/examinations/{exam.pk}/start").status_code == 409

        response = staff.post(
            "/admin/exams/examattempt/",
            {"action": "allow_retake", "_selected_action": [attempt_id]},
        )
        assert response.status_code == 302
        assert ExamResult.objects.count() == 0
        assert api.post(f"/api/examinations/{exam.pk}/start").status_code == 201

    def test_results_cannot_be_deleted_one_by_one(self, staff, api, exam):
        attempt_id = api.post(f"/api/examinations/{exam.pk}/start").json()["attemptId"]
        api.post(
            f"/api/examinations/attempts/{attempt_id}/submit",
            {"reason": "manual"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="k",
        )
        result = ExamResult.objects.get()
        url = f"/admin/exams/examresult/{result.pk}/delete/"
        assert staff.post(url, {"post": "yes"}).status_code == 403
        assert staff.post(f"/admin/exams/examattempt/{attempt_id}/delete/").status_code == 403

    def test_staff_without_the_permission_has_no_retake_action(self, client, api, exam):
        user = get_user_model().objects.create_user("teacher", password="x", is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename="view_examattempt"))
        client.force_login(user)
        attempt_id = api.post(f"/api/examinations/{exam.pk}/start").json()["attemptId"]
        client.post(
            "/admin/exams/examattempt/",
            {"action": "allow_retake", "_selected_action": [attempt_id]},
        )
        assert ExamAttempt.objects.filter(pk=attempt_id).exists()


def exam_data(**overrides) -> dict:
    return {
        "title": "Import test",
        "durationMinutes": 30,
        "sections": [{"subject": "math", "title": "Matematika"}],
        "questions": [
            {
                "number": 1,
                "subject": "math",
                "prompt": text("Savol"),
                "options": [
                    {"label": "A", "content": text("1"), "isCorrect": True},
                    {"label": "B", "content": text("2")},
                ],
            }
        ],
        **overrides,
    }


class TestImportExam:
    def test_valid_file(self, tmp_path):
        path = tmp_path / "exam.json"
        path.write_text(json.dumps(exam_data()), encoding="utf-8")
        call_command("import_exam", str(path), "--publish")
        exam = Exam.objects.get(title="Import test")
        assert exam.is_published
        assert exam.questions.get().options.filter(is_correct=True).count() == 1

    def test_unpublished_by_default(self):
        assert import_exam_data(exam_data()).is_published is False

    @pytest.mark.parametrize(
        "broken",
        [
            lambda d: d["questions"][0]["options"][1].update(isCorrect=True),  # two correct
            lambda d: d["questions"][0]["options"][0].pop("isCorrect"),  # none correct
            lambda d: d["questions"][0].update(prompt="<p>&nbsp;</p>"),  # nothing written
            lambda d: d["questions"][0]["options"][0].update(content="<script>x()</script>"),
            lambda d: d["questions"][0].update(subject="history"),  # unknown subject
            lambda d: d["questions"][0].pop("options"),  # missing field
            lambda d: d.update(durationMinutes=0),  # an exam can't last zero minutes
        ],
    )
    def test_broken_file_saves_nothing(self, broken):
        data = exam_data()
        broken(data)
        with pytest.raises(ValueError):
            import_exam_data(data)
        assert not Exam.objects.filter(title="Import test").exists()

    def test_missing_file_gives_a_readable_error(self):
        with pytest.raises(CommandError):
            call_command("import_exam", "does-not-exist.json")


class TestOtherCommands:
    def test_seed_demo_refuses_outside_debug(self, settings):
        settings.DEBUG = False
        with pytest.raises(CommandError):
            call_command("seed_demo")
        assert not Pupil.objects.exists()

    def test_seed_demo_is_repeatable_and_resets(self, settings):
        settings.DEBUG = True
        call_command("seed_demo", stdout=io.StringIO())
        call_command("seed_demo", stdout=io.StringIO())
        assert Pupil.objects.count() == 3
        assert ExamAttempt.objects.count() == 1

        bobur = Pupil.objects.get(first_name="Bobur")
        result = ExamAttempt.objects.get(pupil=bobur).result
        assert (result.total, result.correct + result.incorrect + result.unanswered) == (45, 45)
        assert bobur.game_sessions.filter(status="completed").count() == 2

        call_command("seed_demo", "--reset", stdout=io.StringIO())
        assert Pupil.objects.count() == 3
        assert ExamAttempt.objects.count() == 1

    def test_finalize_command(self, api, exam, aliya):
        api.post(f"/api/examinations/{exam.pk}/start")
        expire(ExamAttempt.objects.get(pupil=aliya), seconds_past_deadline=3600)
        output = io.StringIO()
        call_command("finalize_expired_attempts", stdout=output)
        assert "1" in output.getvalue()
        assert ExamAttempt.objects.get(pupil=aliya).status == "expired"

    def test_purge_command(self, api, aliya):
        from apps.games.models import Game, GameSession

        game = Game.objects.get(slug="naqsh-ustasi")
        session_id = api.post(f"/api/games/{game.pk}/start", {}, format="json").json()["session"]
        GameSession.objects.filter(pk=session_id["id"]).update(
            started_at=timezone.now() - timedelta(days=2)
        )
        call_command("purge_stale_game_sessions", stdout=io.StringIO())
        assert not GameSession.objects.exists()


class TestErrorFormat:
    def test_unexpected_crash_returns_json_without_internals(self, api, monkeypatch):
        def explode(_pupil):
            raise RuntimeError("secret internal detail")

        monkeypatch.setattr("apps.exams.selectors.dashboard_for", explode)
        response = api.get("/api/student/dashboard")
        assert response.status_code == 500
        assert response.json() == {"code": "INTERNAL_ERROR", "message": "Internal error"}

    def test_malformed_json_body(self, aliya):
        response = client_for().post(
            "/api/auth/jshshir", data="{not json", content_type="application/json"
        )
        assert (response.status_code, response.json()["code"]) == (400, "BAD_REQUEST")

    def test_json_array_body_is_a_validation_error(self, aliya):
        response = client_for().post("/api/auth/jshshir", [1, 2], format="json")
        assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")

    def test_wrong_method(self, aliya):
        response = client_for(aliya).delete("/api/auth/me")
        assert (response.status_code, response.json()["code"]) == (405, "METHOD_NOT_ALLOWED")

    def test_validation_error_does_not_echo_the_jshshir(self, aliya):
        response = client_for().post(
            "/api/auth/jshshir", {"jshshir": "1234567890123X"}, format="json"
        )
        assert "1234567890123X" not in response.content.decode()
