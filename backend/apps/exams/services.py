"""
Exam business rules. Everything that changes an attempt lives here, so the rules stay in one place
and can be tested without HTTP.

Concurrency model: every write takes a row lock on the attempt (`SELECT ... FOR UPDATE`). Answers
for one attempt and its submit therefore run one after another, so an answer can never slip in
after finalisation and an attempt can never be finalised twice. The lock covers a single pupil's
row, so pupils never wait for each other.
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Pupil
from apps.core.exceptions import ApiError

from .layout import draw_layout
from .models import AttemptAnswer, Exam, ExamAttempt, ExamResult, Question, QuestionType, Subject

logger = logging.getLogger(__name__)

Status = ExamAttempt.Status
FinishReason = ExamResult.FinishReason


def start_attempt(pupil: Pupil, exam_id: UUID) -> tuple[ExamAttempt, bool]:
    """Returns (attempt, created). Starting twice returns the same attempt."""
    finalize_overdue_attempts(pupil)

    # 404 for an exam meant for another school: to this pupil it simply doesn't exist.
    exam = Exam.objects.visible_to(pupil).filter(pk=exam_id).first()
    if exam is None:
        raise ApiError(404, "NOT_FOUND")

    existing = ExamAttempt.objects.filter(pupil=pupil, exam=exam).first()
    if existing is not None:
        if existing.status != Status.IN_PROGRESS:
            raise ApiError(409, "ALREADY_COMPLETED")
        return existing, False

    now = timezone.now()
    if not exam.is_open(now) or not exam.questions.exists():
        raise ApiError(403, "EXAM_NOT_AVAILABLE")

    shuffles = exam.shuffle_questions or exam.shuffle_options
    questions = list(exam.questions.prefetch_related("options")) if shuffles else []
    # On a double click, the unique constraint lets one request create the row and the other get it.
    return ExamAttempt.objects.get_or_create(
        pupil=pupil,
        exam=exam,
        defaults={
            "started_at": now,
            "expires_at": now + timedelta(minutes=exam.duration_minutes),
            "layout": draw_layout(exam, questions),
        },
    )


def save_answer(
    pupil: Pupil, attempt_id: UUID, question_id: UUID, option_ids: list[str], client_seq: int
) -> AttemptAnswer:
    with transaction.atomic():
        attempt = _lock_own_attempt(pupil, attempt_id)
        if not attempt.accepts_answers():
            raise ApiError(409, "ATTEMPT_CLOSED")

        question = (
            Question.objects.filter(pk=question_id, exam_id=attempt.exam_id)
            .prefetch_related("options")
            .first()
        )
        if question is None or not _is_valid_selection(question, option_ids):
            raise ApiError(422, "INVALID_ANSWER")

        return _store_answer(attempt, question, option_ids, client_seq)


def submit_attempt(
    pupil: Pupil, attempt_id: UUID, reason: str, unsaved_answers: list[dict]
) -> ExamAttempt:
    """Safe to call many times: only the first call finalises, later ones return the same state."""
    now = timezone.now()
    with transaction.atomic():
        attempt = _lock_own_attempt(pupil, attempt_id)
        if attempt.status == Status.IN_PROGRESS:
            if now <= attempt.submit_deadline:
                _apply_unsaved_answers(attempt, unsaved_answers)
            timed_out = reason == FinishReason.TIMEOUT or now >= attempt.expires_at
            _finalize(attempt, FinishReason.TIMEOUT if timed_out else FinishReason.MANUAL, now)
    return attempt


def finalize_overdue_attempts(pupil: Pupil | None = None) -> int:
    """
    Deadline policy: an attempt past its deadline gets finalised even if the browser never submits.
    Called two ways: for one pupil at the start of their requests, so they never see stale state,
    and for everyone by the `finalize_expired_attempts` cron command.
    """
    now = timezone.now()
    overdue = ExamAttempt.objects.filter(
        status=Status.IN_PROGRESS,
        expires_at__lt=now - timedelta(seconds=settings.EXAM_GRACE_SECONDS),
    )
    if pupil is not None:
        overdue = overdue.filter(pupil=pupil)

    finalized = 0
    # One transaction per attempt: a single broken attempt must not block all the others.
    for attempt_id in overdue.values_list("pk", flat=True):
        try:
            with transaction.atomic():
                attempt = ExamAttempt.objects.select_for_update().get(pk=attempt_id)
                if attempt.status == Status.IN_PROGRESS:  # may have been submitted meanwhile
                    _finalize(attempt, FinishReason.TIMEOUT, now)
                    finalized += 1
        except Exception:
            logger.exception("Could not finalise attempt %s", attempt_id)
    return finalized


def _lock_own_attempt(pupil: Pupil, attempt_id: UUID) -> ExamAttempt:
    attempt = ExamAttempt.objects.select_for_update().filter(pk=attempt_id, pupil=pupil).first()
    if attempt is None:
        # 404 and not 403: another pupil's attempt must look exactly like a missing one.
        raise ApiError(404, "NOT_FOUND")
    return attempt


def _is_valid_selection(question: Question, option_ids: list[str]) -> bool:
    valid_ids = {str(option.pk) for option in question.options.all()}
    if len(set(option_ids)) != len(option_ids) or not set(option_ids) <= valid_ids:
        return False
    return question.type != QuestionType.SINGLE_CHOICE or len(option_ids) <= 1


def _store_answer(
    attempt: ExamAttempt, question: Question, option_ids: list[str], client_seq: int
) -> AttemptAnswer:
    answer = AttemptAnswer.objects.filter(attempt=attempt, question=question).first()
    if answer is None:
        return AttemptAnswer.objects.create(
            attempt=attempt,
            question=question,
            selected_option_ids=option_ids,
            client_seq=client_seq,
        )
    # A slow retry can arrive after a newer choice: a lower seq is stale, so it must not win.
    if client_seq >= answer.client_seq:
        answer.selected_option_ids = option_ids
        answer.client_seq = client_seq
        answer.save()
    return answer


def _apply_unsaved_answers(attempt: ExamAttempt, unsaved_answers: list[dict]) -> None:
    """
    Invalid entries are skipped rather than rejected. This may be the last request a pupil's
    browser ever sends for this exam, so one bad entry must not cost them the whole submission.
    """
    if not unsaved_answers:
        return
    questions = {
        str(question.pk): question
        for question in Question.objects.filter(exam_id=attempt.exam_id).prefetch_related("options")
    }
    for item in unsaved_answers:
        question = questions.get(item["questionId"])
        if question and _is_valid_selection(question, item["selectedOptionIds"]):
            _store_answer(attempt, question, item["selectedOptionIds"], item["clientSeq"])


def _finalize(attempt: ExamAttempt, reason: str, now: datetime) -> ExamResult:
    attempt.status = Status.EXPIRED if reason == FinishReason.TIMEOUT else Status.SUBMITTED
    attempt.save(update_fields=["status"])
    return ExamResult.objects.create(
        attempt=attempt,
        finish_reason=reason,
        # A pupil never "finishes" later than the deadline, however late the job runs.
        completed_at=min(now, attempt.expires_at),
        **_grade(attempt),
    )


def _grade(attempt: ExamAttempt) -> dict:
    """Scores are only ever computed here, on the server, from the stored answers."""
    selected = {answer.question_id: answer.selected_option_ids for answer in attempt.answers.all()}
    questions = Question.objects.filter(exam_id=attempt.exam_id).prefetch_related("options")

    by_subject: dict[str, dict] = {}
    for question in questions:
        stats = by_subject.setdefault(
            question.subject, {"correct": 0, "incorrect": 0, "unanswered": 0, "total": 0}
        )
        stats["total"] += 1
        chosen = set(selected.get(question.pk, []))
        correct = {str(option.pk) for option in question.options.all() if option.is_correct}
        if not chosen:
            stats["unanswered"] += 1
        elif chosen == correct:
            stats["correct"] += 1
        else:
            stats["incorrect"] += 1

    subjects = [
        {"subject": subject, **stats, "percent": stats["correct"] / stats["total"] * 100}
        for subject, stats in sorted(by_subject.items(), key=lambda kv: Subject.values.index(kv[0]))
    ]
    correct = sum(item["correct"] for item in subjects)
    total = sum(item["total"] for item in subjects)
    points = attempt.exam.points_per_question
    return {
        "correct": correct,
        "incorrect": sum(item["incorrect"] for item in subjects),
        "unanswered": sum(item["unanswered"] for item in subjects),
        "total": total,
        "score": correct * points,
        "max_score": total * points,
        "percent": correct / total * 100 if total else 0,
        "subjects": subjects,
    }
