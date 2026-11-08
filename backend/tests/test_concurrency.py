"""
The promises that only hold if the database enforces them: these run real parallel transactions
against PostgreSQL. `transaction=True` is needed so that each thread sees committed data.
"""

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection

from apps.accounts.services import authenticate_by_qr, issue_qr_token
from apps.core.exceptions import ApiError
from apps.exams.models import AttemptAnswer, ExamAttempt, ExamResult
from apps.exams.services import save_answer, start_attempt, submit_attempt
from apps.games import services as games
from apps.games.models import DailyChallengeCompletion, DailyQuestionAnswer, Game

from .conftest import make_exam, make_pupil, options_of

# serialized_rollback restores the catalogue created by migrations, which `transaction=True` wipes.
pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

WORKERS = 8


def run_in_parallel(function, times=WORKERS) -> list:
    """Runs `function` from many threads at once; returns each result or the exception raised."""

    def worker(_):
        try:
            return function()
        except ApiError as error:
            return error
        finally:
            connection.close()  # each thread owns its database connection

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(worker, range(times)))


def test_parallel_start_creates_one_attempt():
    pupil, exam = make_pupil("11111111111111", "A"), make_exam()
    results = run_in_parallel(lambda: start_attempt(pupil, exam.pk))
    assert {attempt.pk for attempt, _created in results} == {ExamAttempt.objects.get().pk}
    assert sum(created for _attempt, created in results) == 1


def test_parallel_submit_finalises_once():
    pupil, exam = make_pupil("11111111111111", "A"), make_exam()
    attempt, _ = start_attempt(pupil, exam.pk)
    results = run_in_parallel(lambda: submit_attempt(pupil, attempt.pk, "manual", []))
    assert ExamResult.objects.count() == 1
    assert {r.status for r in results} == {"submitted"}


def test_highest_seq_wins_whatever_order_requests_arrive_in():
    pupil, exam = make_pupil("11111111111111", "A"), make_exam()
    attempt, _ = start_attempt(pupil, exam.pk)
    question = exam.questions.first()
    right, wrong = options_of(question)
    sequence = iter(range(1, 41))  # shared: each call takes the next number when it starts

    def save():
        seq = next(sequence)
        choice = right if seq == 40 else wrong
        return save_answer(pupil, attempt.pk, question.pk, [choice], seq)

    run_in_parallel(save, times=40)
    answer = AttemptAnswer.objects.get()
    assert (answer.client_seq, answer.selected_option_ids) == (40, [right])


def test_answers_for_different_questions_do_not_overwrite_each_other():
    pupil, exam = make_pupil("11111111111111", "A"), make_exam()
    attempt, _ = start_attempt(pupil, exam.pk)
    questions = iter(list(exam.questions.all()))

    def save():
        question = next(questions)
        return save_answer(pupil, attempt.pk, question.pk, [options_of(question)[0]], 1)

    run_in_parallel(save, times=6)
    assert AttemptAnswer.objects.filter(attempt=attempt).count() == 6


def test_answer_racing_with_submit_is_either_counted_or_refused():
    """The invariant: the stored score always matches the answers that were accepted."""
    pupil, exam = make_pupil("11111111111111", "A"), make_exam()
    attempt, _ = start_attempt(pupil, exam.pk)
    questions = list(exam.questions.all())
    tasks = iter(
        [lambda: submit_attempt(pupil, attempt.pk, "manual", [])]
        + [
            (lambda q=q: save_answer(pupil, attempt.pk, q.pk, [options_of(q)[0]], 1))
            for q in questions
        ]
    )

    run_in_parallel(lambda: next(tasks)(), times=len(questions) + 1)

    assert ExamResult.objects.get().correct == AttemptAnswer.objects.count()


def test_qr_token_cannot_be_used_twice_at_once():
    # Several rounds: this race doesn't show up on every run, and it once slipped through that way.
    pupil = make_pupil("11111111111111", "A")
    for _ in range(15):
        token, _entry = issue_qr_token(pupil)
        results = run_in_parallel(lambda token=token: authenticate_by_qr(token))
        errors = [r for r in results if isinstance(r, ApiError)]
        assert len(results) - len(errors) == 1
        assert {error.code for error in errors} == {"QR_ALREADY_USED"}


def _daily_session(pupil):
    challenge = games.daily_challenge(pupil)
    return games.start_game(pupil, challenge.game.pk, challenge.difficulty, True)


def _finish(pupil, session):
    moves = None
    if session.content["kind"] == "memory":
        by_face = {}
        for card in session.content["cards"]:
            by_face.setdefault(card["face"], []).append(card["id"])
        moves = list(by_face.values())
    return games.complete_game(pupil, session.pk, moves)


def test_parallel_complete_of_one_session_is_rewarded_once():
    pupil = make_pupil("11111111111111", "A")
    session = _daily_session(pupil)
    results = run_in_parallel(lambda: _finish(pupil, session))
    assert {r.bonus for r in results} == {games.DAILY_BONUS}
    assert DailyChallengeCompletion.objects.count() == 1


def test_parallel_daily_sessions_earn_one_bonus():
    pupil = make_pupil("11111111111111", "A")
    sessions = iter([_daily_session(pupil) for _ in range(WORKERS)])
    assert Game.objects.filter(is_active=True).exists()

    results = run_in_parallel(lambda: _finish(pupil, next(sessions)))

    assert sorted(r.bonus for r in results) == [0] * (WORKERS - 1) + [games.DAILY_BONUS]
    assert DailyChallengeCompletion.objects.count() == 1


def test_parallel_daily_question_answers_keep_one():
    pupil = make_pupil("11111111111111", "A")
    question = games.daily_question_state(pupil).question
    results = run_in_parallel(
        lambda: games.answer_daily_question(pupil, None, question.correct_option_id)
    )
    assert DailyQuestionAnswer.objects.count() == 1
    assert {r.answer.pk for r in results} == {DailyQuestionAnswer.objects.get().pk}
