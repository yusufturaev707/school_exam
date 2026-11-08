from datetime import timedelta
from uuid import uuid4

import pytest
from django.db.models import ProtectedError
from django.utils import timezone

from apps.exams.models import Exam, ExamAttempt, ExamResult
from apps.exams.services import finalize_overdue_attempts

from .conftest import client_for, expire, options_of

pytestmark = pytest.mark.django_db

NOW_MS = (
    1_793_000_000_000  # wall-clock milliseconds, the real magnitude of the frontend's clientSeq
)


def start(api, exam) -> str:
    response = api.post(f"/api/examinations/{exam.pk}/start")
    assert response.status_code in (200, 201), response.content
    return response.json()["attemptId"]


def save(api, attempt_id, question, option_ids, seq=NOW_MS):
    return api.put(
        f"/api/examinations/attempts/{attempt_id}/answers/{question.pk}",
        {"selectedOptionIds": option_ids, "clientSeq": seq},
        format="json",
    )


def submit(api, attempt_id, reason="manual", unsaved=None, key="key-1"):
    headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
    return api.post(
        f"/api/examinations/attempts/{attempt_id}/submit",
        {"reason": reason, "unsavedAnswers": unsaved or []},
        format="json",
        **headers,
    )


def stored_answers(api, attempt_id) -> dict:
    return api.get(f"/api/examinations/attempts/{attempt_id}").json()["answers"]


class TestStart:
    def test_first_start_creates_and_second_returns_the_same_attempt(self, api, exam):
        first = api.post(f"/api/examinations/{exam.pk}/start")
        second = api.post(f"/api/examinations/{exam.pk}/start")
        assert (first.status_code, second.status_code) == (201, 200)
        assert first.json() == second.json()
        assert ExamAttempt.objects.count() == 1

    def test_deadline_comes_from_exam_duration(self, api, exam, aliya):
        start(api, exam)
        attempt = ExamAttempt.objects.get(pupil=aliya)
        assert attempt.expires_at - attempt.started_at == timedelta(minutes=60)

    def test_finished_exam_cannot_be_started_again(self, api, exam):
        submit(api, start(api, exam))
        response = api.post(f"/api/examinations/{exam.pk}/start")
        assert (response.status_code, response.json()["code"]) == (409, "ALREADY_COMPLETED")

    def test_exam_outside_its_window_is_not_available(self, api, exam):
        Exam.objects.filter(pk=exam.pk).update(available_from=timezone.now() + timedelta(hours=1))
        response = api.post(f"/api/examinations/{exam.pk}/start")
        assert (response.status_code, response.json()["code"]) == (403, "EXAM_NOT_AVAILABLE")

        listed = api.get("/api/examinations/available").json()["examinations"][0]
        assert listed["status"] == "unavailable"
        assert listed["availableFrom"].endswith("Z")

    def test_unpublished_exam_is_invisible(self, api, exam):
        Exam.objects.filter(pk=exam.pk).update(is_published=False)
        assert api.get("/api/examinations/available").json()["examinations"] == []
        assert api.post(f"/api/examinations/{exam.pk}/start").status_code == 404


class TestAttemptPayload:
    def test_never_contains_correct_answers_or_explanations(self, api, exam):
        response = api.get(f"/api/examinations/attempts/{start(api, exam)}")
        body = response.json()
        assert len(body["questions"]) == 6
        assert set(body["questions"][0]) == {
            "id",
            "number",
            "subject",
            "type",
            "prompt",
            "passage",
            "options",
        }
        assert set(body["questions"][0]["options"][0]) == {"id", "label", "content"}
        assert "isCorrect" not in response.content.decode()
        assert "Izoh" not in response.content.decode()

    def test_timestamps_are_utc(self, api, exam):
        body = api.get(f"/api/examinations/attempts/{start(api, exam)}").json()
        for field in ("startedAt", "expiresAt", "serverTime"):
            assert body[field].endswith("Z")

    def test_section_counts(self, api, exam):
        body = api.get(f"/api/examinations/attempts/{start(api, exam)}").json()
        assert [(s["subject"], s["questionCount"]) for s in body["sections"]] == [
            ("math", 2),
            ("iq", 2),
            ("language", 2),
        ]

    def test_questions_are_not_sent_after_finishing(self, api, exam):
        attempt_id = start(api, exam)
        submit(api, attempt_id)
        body = api.get(f"/api/examinations/attempts/{attempt_id}").json()
        assert body["questions"] == []
        assert body["status"] == "submitted"
        assert body["resultId"]


class TestAnswers:
    def test_saved_answer_comes_back_on_reload(self, api, exam):
        attempt_id = start(api, exam)
        question = exam.questions.first()
        right, _ = options_of(question)
        response = save(api, attempt_id, question, [right])
        assert response.status_code == 200
        assert response.json()["questionId"] == str(question.pk)
        assert stored_answers(api, attempt_id) == {str(question.pk): [right]}

    def test_late_retry_cannot_overwrite_a_newer_choice(self, api, exam):
        attempt_id = start(api, exam)
        question = exam.questions.first()
        right, wrong = options_of(question)
        save(api, attempt_id, question, [right], seq=NOW_MS + 5)
        # The older request still reports success, but must not change anything.
        assert save(api, attempt_id, question, [wrong], seq=NOW_MS + 1).status_code == 200
        assert stored_answers(api, attempt_id) == {str(question.pk): [right]}

    def test_clearing_an_answer(self, api, exam):
        attempt_id = start(api, exam)
        question = exam.questions.first()
        save(api, attempt_id, question, [options_of(question)[0]], seq=NOW_MS)
        save(api, attempt_id, question, [], seq=NOW_MS + 1)
        assert stored_answers(api, attempt_id) == {str(question.pk): []}

    @pytest.mark.parametrize("build_ids", [lambda r, w: ["nope"], lambda r, w: [r, w]])
    def test_invalid_selection_is_rejected(self, api, exam, build_ids):
        attempt_id = start(api, exam)
        question = exam.questions.first()
        response = save(api, attempt_id, question, build_ids(*options_of(question)))
        assert (response.status_code, response.json()["code"]) == (422, "INVALID_ANSWER")

    def test_question_from_another_exam_is_rejected(self, api, exam):
        attempt_id = start(api, exam)
        from .conftest import make_exam

        foreign = make_exam(title="Boshqa").questions.first()
        response = save(api, attempt_id, foreign, [options_of(foreign)[0]])
        assert (response.status_code, response.json()["code"]) == (422, "INVALID_ANSWER")

    def test_closed_after_deadline_even_before_the_job_runs(self, api, exam, aliya):
        attempt_id = start(api, exam)
        expire(ExamAttempt.objects.get(pupil=aliya), seconds_past_deadline=1)
        question = exam.questions.first()
        response = save(api, attempt_id, question, [options_of(question)[0]])
        assert (response.status_code, response.json()["code"]) == (409, "ATTEMPT_CLOSED")

    def test_closed_after_submit(self, api, exam):
        attempt_id = start(api, exam)
        submit(api, attempt_id)
        question = exam.questions.first()
        response = save(api, attempt_id, question, [options_of(question)[0]])
        assert (response.status_code, response.json()["code"]) == (409, "ATTEMPT_CLOSED")


class TestSubmit:
    def test_requires_idempotency_key(self, api, exam):
        response = submit(api, start(api, exam), key=None)
        assert (response.status_code, response.json()["code"]) == (400, "IDEMPOTENCY_KEY_REQUIRED")

    def test_repeats_return_the_same_state_and_one_result(self, api, exam):
        attempt_id = start(api, exam)
        first = submit(api, attempt_id, key="a")
        second = submit(api, attempt_id, key="b")
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert first.json()["status"] == "submitted"
        assert ExamResult.objects.count() == 1

    def test_unsaved_answers_are_applied_respecting_seq(self, api, exam):
        attempt_id = start(api, exam)
        q1, q2 = list(exam.questions.all())[:2]
        q1_right, q1_wrong = options_of(q1)
        q2_right, _ = options_of(q2)
        save(api, attempt_id, q1, [q1_right], seq=NOW_MS + 5)

        submit(
            api,
            attempt_id,
            unsaved=[
                {"questionId": str(q1.pk), "selectedOptionIds": [q1_wrong], "clientSeq": NOW_MS},
                {"questionId": str(q2.pk), "selectedOptionIds": [q2_right], "clientSeq": NOW_MS},
            ],
        )
        assert stored_answers(api, attempt_id) == {str(q1.pk): [q1_right], str(q2.pk): [q2_right]}

    def test_a_bad_unsaved_entry_does_not_lose_the_submission(self, api, exam):
        attempt_id = start(api, exam)
        question = exam.questions.first()
        right, _ = options_of(question)
        response = submit(
            api,
            attempt_id,
            unsaved=[
                {"questionId": "unknown", "selectedOptionIds": ["x"], "clientSeq": 1},
                {"questionId": str(question.pk), "selectedOptionIds": ["x"], "clientSeq": 1},
                {"questionId": str(question.pk), "selectedOptionIds": [right], "clientSeq": 2},
            ],
        )
        assert response.status_code == 200
        assert stored_answers(api, attempt_id) == {str(question.pk): [right]}

    def test_within_grace_period_unsaved_answers_still_count(self, api, exam, aliya, settings):
        settings.EXAM_GRACE_SECONDS = 30
        attempt_id = start(api, exam)
        expire(ExamAttempt.objects.get(pupil=aliya), seconds_past_deadline=5)
        question = exam.questions.first()
        right, _ = options_of(question)
        response = submit(
            api,
            attempt_id,
            reason="timeout",
            unsaved=[
                {"questionId": str(question.pk), "selectedOptionIds": [right], "clientSeq": 1}
            ],
        )
        assert response.json()["status"] == "expired"
        assert ExamResult.objects.get().correct == 1

    def test_after_grace_period_unsaved_answers_are_ignored(self, api, exam, aliya, settings):
        settings.EXAM_GRACE_SECONDS = 30
        attempt_id = start(api, exam)
        expire(ExamAttempt.objects.get(pupil=aliya), seconds_past_deadline=60)
        question = exam.questions.first()
        right, _ = options_of(question)
        response = submit(
            api,
            attempt_id,
            reason="timeout",
            unsaved=[
                {"questionId": str(question.pk), "selectedOptionIds": [right], "clientSeq": 1}
            ],
        )
        assert response.json()["status"] == "expired"
        assert ExamResult.objects.get().correct == 0

    def test_submit_at_deadline_counts_as_timeout_whatever_the_client_says(self, api, exam, aliya):
        attempt_id = start(api, exam)
        expire(ExamAttempt.objects.get(pupil=aliya), seconds_past_deadline=1)
        submit(api, attempt_id, reason="manual")
        assert ExamResult.objects.get().finish_reason == "timeout"


class TestDeadlinePolicy:
    def test_job_finalises_attempts_nobody_submitted_and_keeps_answers(self, api, exam, aliya):
        attempt_id = start(api, exam)
        question = exam.questions.first()
        save(api, attempt_id, question, [options_of(question)[0]])
        attempt = ExamAttempt.objects.get(pupil=aliya)
        expire(attempt, seconds_past_deadline=3600)

        assert finalize_overdue_attempts() == 1
        attempt.refresh_from_db()
        assert attempt.status == "expired"

        result = attempt.result
        assert (result.correct, result.unanswered, result.finish_reason) == (1, 5, "timeout")
        assert result.completed_at == attempt.expires_at  # not the moment the job happened to run
        assert finalize_overdue_attempts() == 0

    def test_grace_period_is_respected(self, api, exam, aliya, settings):
        settings.EXAM_GRACE_SECONDS = 30
        start(api, exam)
        expire(ExamAttempt.objects.get(pupil=aliya), seconds_past_deadline=5)
        assert finalize_overdue_attempts() == 0

    def test_finalised_on_next_access_without_the_job(self, api, exam, aliya):
        start(api, exam)
        expire(ExamAttempt.objects.get(pupil=aliya), seconds_past_deadline=3600)
        listed = api.get("/api/examinations/available").json()["examinations"][0]
        assert listed["status"] == "completed"
        assert listed["activeAttemptId"] is None
        assert listed["resultId"]


class TestResults:
    def finished(self, api, exam):
        """Answers: 2 right, 1 wrong, 3 blank. Two right in math, one wrong in iq."""
        attempt_id = start(api, exam)
        questions = list(exam.questions.all())
        save(api, attempt_id, questions[0], [options_of(questions[0])[0]])
        save(api, attempt_id, questions[1], [options_of(questions[1])[0]])
        save(api, attempt_id, questions[2], [options_of(questions[2])[1]])
        return submit(api, attempt_id).json()["resultId"]

    def test_scores(self, api, exam):
        result = api.get(f"/api/student/results/{self.finished(api, exam)}").json()
        totals = result["totals"]
        assert (totals["correct"], totals["incorrect"], totals["unanswered"]) == (2, 1, 3)
        assert (totals["score"], totals["maxScore"], totals["total"]) == (4, 12, 6)
        assert totals["percent"] == pytest.approx(100 * 2 / 6)

        by_subject = {s["subject"]: s for s in result["subjects"]}
        assert by_subject["math"]["percent"] == 100
        assert by_subject["iq"]["incorrect"] == 1
        assert by_subject["language"]["unanswered"] == 2

    def test_review_included_when_policy_allows(self, api, exam):
        review = api.get(f"/api/student/results/{self.finished(api, exam)}").json()["review"]
        assert review["enabled"] is True
        assert len(review["items"]) == 6
        first = review["items"][0]
        assert first["selectedOptionIds"] == first["correctOptionIds"]
        assert first["explanation"] == [{"type": "html", "html": "<p>Izoh 1</p>"}]

    def test_review_hidden_when_policy_forbids(self, api, exam):
        result_id = self.finished(api, exam)
        Exam.objects.filter(pk=exam.pk).update(review_enabled=False)
        response = api.get(f"/api/student/results/{result_id}")
        assert response.json()["review"] == {"enabled": False}
        assert "Izoh" not in response.content.decode()

    def test_score_is_a_snapshot(self, api, exam):
        result_id = self.finished(api, exam)
        for question in exam.questions.all():
            question.options.update(is_correct=False)
        assert api.get(f"/api/student/results/{result_id}").json()["totals"]["correct"] == 2

    def test_results_list(self, api, exam):
        result_id = self.finished(api, exam)
        results = api.get("/api/student/results").json()["results"]
        assert [r["id"] for r in results] == [result_id]
        assert (results[0]["correct"], results[0]["total"]) == (2, 6)

    def test_answered_question_cannot_be_deleted(self, api, exam):
        self.finished(api, exam)
        with pytest.raises(ProtectedError):
            exam.questions.first().delete()


class TestDashboard:
    def test_new_pupil_has_null_stats_not_zeros(self, api, exam):
        body = api.get("/api/student/dashboard").json()
        assert body["student"] == {"firstName": "Aliya"}
        assert body["stats"]["overallPercent"] is None
        assert body["stats"]["completedExams"] == 0
        assert all(s["percent"] is None for s in body["stats"]["subjects"])
        assert body["examinations"][0]["status"] == "available"
        assert body["recentActivity"] == []

    def test_in_progress_then_completed(self, api, exam):
        attempt_id = start(api, exam)
        summary = api.get("/api/student/dashboard").json()["examinations"][0]
        assert summary["status"] == "in_progress"
        assert summary["activeAttemptId"] == attempt_id

        submit(api, attempt_id)
        body = api.get("/api/student/dashboard").json()
        assert body["examinations"][0]["status"] == "completed"
        assert body["stats"]["completedExams"] == 1
        assert body["stats"]["overallPercent"] == 0
        assert body["recentActivity"][0]["status"] == "completed"

    def test_query_count_does_not_grow_with_questions(
        self, api, exam, django_assert_max_num_queries
    ):
        start(api, exam)
        with django_assert_max_num_queries(12):
            assert api.get("/api/student/dashboard").status_code == 200


class TestIsolation:
    """Another pupil's data must look exactly like data that doesn't exist."""

    def test_attempt_is_404_for_another_pupil(self, api, exam, bek):
        attempt_id = start(api, exam)
        question = exam.questions.first()
        intruder = client_for(bek)
        assert intruder.get(f"/api/examinations/attempts/{attempt_id}").status_code == 404
        assert save(intruder, attempt_id, question, []).status_code == 404
        assert submit(intruder, attempt_id).status_code == 404
        assert ExamAttempt.objects.get(pk=attempt_id).status == "in_progress"

    def test_result_is_404_for_another_pupil(self, api, exam, bek):
        result_id = submit(api, start(api, exam)).json()["resultId"]
        intruder = client_for(bek)
        assert intruder.get(f"/api/student/results/{result_id}").status_code == 404
        assert intruder.get("/api/student/results").json()["results"] == []

    def test_unknown_id_gives_the_same_answer(self, api):
        assert api.get(f"/api/examinations/attempts/{uuid4()}").status_code == 404

    @pytest.mark.parametrize(
        "path",
        [
            "/api/student/dashboard",
            "/api/student/results",
            "/api/examinations/available",
            "/api/games",
            "/api/student/achievements",
        ],
    )
    def test_anonymous_requests_are_401(self, path):
        response = client_for().get(path)
        assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
