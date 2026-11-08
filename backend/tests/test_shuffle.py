"""
One question set for everybody, but every pupil gets their own question order and option letters.
Uses the real 4th-grade diagnostic test from content/, so its structure is checked as well.
"""

import json
import re
import uuid
from collections import Counter
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.exams.importer import import_exam_data
from apps.exams.layout import draw_layout
from apps.exams.models import AnswerOption, ExamAttempt, ExamTarget, Question
from apps.exams.selectors import attempt_questions

from .conftest import client_for, make_exam, make_region, text

CONTENT = Path(settings.BASE_DIR) / "content" / "diagnostika-4-sinf.json"
SECTIONS = ["math", "iq", "language"]


@pytest.fixture
def diagnostic(db):
    exam = import_exam_data(json.loads(CONTENT.read_text(encoding="utf-8")), publish=True)
    # The file assigns it to 4th grades; the test pupils are in a 5th grade, so add their region.
    ExamTarget.objects.create(exam=exam, region=make_region())
    return exam


def start(client, exam) -> str:
    response = client.post(f"/api/examinations/{exam.pk}/start")
    assert response.status_code in (200, 201), response.content
    return response.json()["attemptId"]


def shown(client, attempt_id) -> list[dict]:
    return client.get(f"/api/examinations/attempts/{attempt_id}").json()["questions"]


def answer_key(attempt_id) -> list[tuple[str, str]]:
    attempt = ExamAttempt.objects.select_related("exam").get(pk=attempt_id)
    return [
        (str(q.id), next(o.label for o in q.options if o.is_correct))
        for q in attempt_questions(attempt)
    ]


class TestDiagnosticContent:
    def test_thirty_questions_ten_per_subject_in_three_levels(self, diagnostic):
        questions = list(diagnostic.questions.all())
        assert len(questions) == 30
        assert Counter(q.subject for q in questions) == {"math": 10, "iq": 10, "language": 10}
        for subject in SECTIONS:
            levels = [q.difficulty for q in questions if q.subject == subject]
            assert levels == [1, 1, 1, 2, 2, 2, 2, 3, 3, 3]

    def test_scoring_and_policy(self, diagnostic):
        assert diagnostic.points_per_question == 1
        assert diagnostic.shuffle_questions and diagnostic.shuffle_options
        assert not diagnostic.review_enabled
        assert diagnostic.targets.filter(grade=4).exists()

    def test_every_question_has_four_distinct_options_and_one_answer(self, diagnostic):
        for question in diagnostic.questions.prefetch_related("options"):
            options = list(question.options.all())
            assert len(options) == 4
            assert len({o.content for o in options}) == 4, question.number
            assert sum(o.is_correct for o in options) == 1, question.number

    def test_pictures_are_stored_inside_the_questions(self, diagnostic):
        sources = [
            src
            for question in diagnostic.questions.all()
            for src in re.findall(r'<img src="([^"]+)"', question.prompt)
        ]
        assert len(sources) == 9
        assert all(src.startswith("data:image/svg+xml;base64,") for src in sources)

    def test_the_file_matches_its_generator(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "diagnostika", CONTENT.with_name("diagnostika_4_sinf.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.build() == json.loads(CONTENT.read_text(encoding="utf-8"))


@pytest.mark.django_db
class TestShuffledAttempt:
    def test_same_questions_in_a_different_order_for_each_pupil(self, diagnostic, aliya, bek):
        aliya_id, bek_id = start(client_for(aliya), diagnostic), start(client_for(bek), diagnostic)
        for_aliya, for_bek = shown(client_for(aliya), aliya_id), shown(client_for(bek), bek_id)

        assert {q["id"] for q in for_aliya} == {q["id"] for q in for_bek}
        assert [q["id"] for q in for_aliya] != [q["id"] for q in for_bek]
        assert answer_key(aliya_id) != answer_key(bek_id)
        for questions in (for_aliya, for_bek):
            assert [q["number"] for q in questions] == list(range(1, 31))
            assert all([o["label"] for o in q["options"]] == list("ABCD") for q in questions)

    def test_subjects_stay_together_and_go_from_easy_to_hard(self, diagnostic, aliya):
        client = client_for(aliya)
        questions = shown(client, start(client, diagnostic))
        level = dict(diagnostic.questions.values_list("pk", "difficulty"))
        subjects = [q["subject"] for q in questions]
        assert subjects == sorted(subjects, key=SECTIONS.index)
        for subject in SECTIONS:
            levels = [level[uuid.UUID(q["id"])] for q in questions if q["subject"] == subject]
            assert levels == sorted(levels)

    def test_orders_really_vary(self, diagnostic):
        questions = list(diagnostic.questions.prefetch_related("options"))
        orders = {tuple(draw_layout(diagnostic, questions)["questions"]) for _ in range(20)}
        assert len(orders) > 1

    def test_the_order_is_kept_and_survives_editing_the_exam(self, diagnostic, aliya):
        client = client_for(aliya)
        attempt_id = start(client, diagnostic)
        before = shown(client, attempt_id)
        assert shown(client, attempt_id) == before

        extra = Question.objects.create(
            exam=diagnostic, number=31, subject="math", prompt=text("Yangi savol")
        )
        AnswerOption.objects.create(question=extra, label="A", content=text("1"), is_correct=True)
        after = shown(client, attempt_id)
        math_ids = [q["id"] for q in after if q["subject"] == "math"]
        assert math_ids[-1] == str(extra.pk)
        assert [q["id"] for q in after if q["id"] != str(extra.pk)] == [q["id"] for q in before]

    def test_scoring_does_not_depend_on_letters(self, diagnostic, aliya):
        client = client_for(aliya)
        attempt_id = start(client, diagnostic)
        correct = dict(AnswerOption.objects.filter(is_correct=True).values_list("question", "pk"))
        for seq, question in enumerate(shown(client, attempt_id), start=1):
            response = client.put(
                f"/api/examinations/attempts/{attempt_id}/answers/{question['id']}",
                {"selectedOptionIds": [str(correct[uuid.UUID(question["id"])])], "clientSeq": seq},
                format="json",
            )
            assert response.status_code == 200, response.content
        result = client.post(
            f"/api/examinations/attempts/{attempt_id}/submit",
            {"reason": "manual"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        ).json()
        totals = client.get(f"/api/student/results/{result['resultId']}").json()["totals"]
        assert (totals["score"], totals["maxScore"]) == (30, 30)

    def test_review_shows_the_pupils_own_order_and_letters(self, diagnostic, aliya):
        diagnostic.review_enabled = True
        diagnostic.save()
        client = client_for(aliya)
        attempt_id = start(client, diagnostic)
        during = shown(client, attempt_id)
        result = client.post(
            f"/api/examinations/attempts/{attempt_id}/submit",
            {"reason": "manual"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        ).json()
        items = client.get(f"/api/student/results/{result['resultId']}").json()["review"]["items"]
        assert [(i["questionId"], i["number"]) for i in items] == [
            (q["id"], q["number"]) for q in during
        ]
        assert [[o["id"] for o in i["options"]] for i in items] == [
            [o["id"] for o in q["options"]] for q in during
        ]

    def test_without_shuffling_nothing_changes(self, aliya):
        exam = make_exam()
        client = client_for(aliya)
        attempt_id = start(client, exam)
        assert ExamAttempt.objects.get(pk=attempt_id).layout == {}
        questions = shown(client, attempt_id)
        assert [q["number"] for q in questions] == [1, 2, 3, 4, 5, 6]

    def test_admin_shows_the_pupils_answer_key(self, diagnostic, aliya, client):
        attempt_id = start(client_for(aliya), diagnostic)
        client.force_login(get_user_model().objects.create_superuser("admin", password="x"))
        page = client.get(f"/admin/exams/examattempt/{attempt_id}/change/").content.decode()
        compact = ", ".join(
            f"{n}-{label}" for n, (_, label) in enumerate(answer_key(attempt_id), 1)
        )
        assert "Javob kaliti" in page
        assert compact in re.sub(r"<[^>]+>", "", page)
