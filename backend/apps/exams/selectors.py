"""
Read side: gathers data for responses without N+1 queries. Serializers turn the results into JSON.

Most functions begin with `finalize_overdue_attempts`, which is the "or on next access" half of the
deadline policy: a pupil must never see an attempt as running when its time is long over.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.db.models import Count
from django.utils import timezone

from apps.accounts.models import Pupil
from apps.core.exceptions import ApiError

from .models import Exam, ExamAttempt, ExamResult, Question, Subject
from .services import finalize_overdue_attempts

Status = ExamAttempt.Status


@dataclass(frozen=True)
class SectionInfo:
    subject: str
    title: str
    question_count: int


@dataclass(frozen=True)
class ExamSummary:
    id: UUID
    title: str
    description: str
    total_questions: int
    duration_minutes: int
    sections: list[SectionInfo]
    status: str
    active_attempt_id: UUID | None
    result_id: UUID | None
    available_from: datetime | None


@dataclass(frozen=True)
class AttemptSession:
    attempt: ExamAttempt
    sections: list[SectionInfo]
    questions: list[Question]
    answers: dict[str, list[str]]
    server_time: datetime


def exam_summaries(pupil: Pupil) -> list[ExamSummary]:
    finalize_overdue_attempts(pupil)
    now = timezone.now()

    exams = list(Exam.objects.visible_to(pupil).prefetch_related("sections"))
    counts = _question_counts(exams)
    attempts = {
        attempt.exam_id: attempt
        for attempt in ExamAttempt.objects.filter(pupil=pupil).select_related("result")
    }

    summaries = []
    for exam in exams:
        exam_counts = counts.get(exam.pk, {})
        total = sum(exam_counts.values())
        if total == 0:
            continue  # the contract requires totalQuestions > 0, and it's not ready to show anyway

        attempt = attempts.get(exam.pk)
        summaries.append(
            ExamSummary(
                id=exam.pk,
                title=exam.title,
                description=exam.description,
                total_questions=total,
                duration_minutes=exam.duration_minutes,
                sections=_sections(exam, exam_counts),
                status=_pupil_status(exam, attempt, now),
                active_attempt_id=(
                    attempt.pk if attempt and attempt.status == Status.IN_PROGRESS else None
                ),
                result_id=attempt.result_id if attempt else None,
                available_from=exam.available_from,
            )
        )
    return summaries


def attempt_session(pupil: Pupil, attempt_id: UUID) -> AttemptSession:
    finalize_overdue_attempts(pupil)

    attempt = (
        ExamAttempt.objects.select_related("exam", "result")
        .prefetch_related("exam__sections", "answers")
        .filter(pk=attempt_id, pupil=pupil)
        .first()
    )
    if attempt is None:
        raise ApiError(404, "NOT_FOUND")

    # Questions are only sent while the exam is running. Afterwards the result screen takes over.
    questions = []
    if attempt.status == Status.IN_PROGRESS:
        questions = list(attempt.exam.questions.prefetch_related("options"))

    counts = _question_counts([attempt.exam]).get(attempt.exam_id, {})
    return AttemptSession(
        attempt=attempt,
        sections=_sections(attempt.exam, counts),
        questions=questions,
        answers={str(a.question_id): a.selected_option_ids for a in attempt.answers.all()},
        server_time=timezone.now(),
    )


def results_for(pupil: Pupil) -> list[ExamResult]:
    finalize_overdue_attempts(pupil)
    return list(ExamResult.objects.filter(attempt__pupil=pupil).select_related("attempt__exam"))


def result_for(pupil: Pupil, result_id: UUID) -> ExamResult:
    result = (
        ExamResult.objects.select_related("attempt__exam")
        .filter(pk=result_id, attempt__pupil=pupil)
        .first()
    )
    if result is None:
        raise ApiError(404, "NOT_FOUND")
    return result


def review_items(result: ExamResult) -> list[dict]:
    selected = {
        answer.question_id: answer.selected_option_ids for answer in result.attempt.answers.all()
    }
    return [
        {
            "question_id": question.pk,
            "number": question.number,
            "subject": question.subject,
            "prompt": question.prompt,
            "passage": question.passage,
            "options": question.options.all(),
            "selected_option_ids": selected.get(question.pk, []),
            "correct_option_ids": [str(o.pk) for o in question.options.all() if o.is_correct],
            "explanation": question.explanation,
        }
        for question in result.attempt.exam.questions.prefetch_related("options")
    ]


def dashboard_for(pupil: Pupil) -> dict:
    summaries = exam_summaries(pupil)
    results = results_for(pupil)
    return {
        "pupil": pupil,
        "examinations": summaries,
        "stats": {
            "total_exams": len(summaries),
            "completed_exams": len(results),
            "overall_percent": _average([result.percent for result in results]),
            "subjects": [
                {"subject": subject, "percent": _subject_average(results, subject)}
                for subject in Subject.values
            ],
        },
        "recent_activity": results[:5],
    }


def _pupil_status(exam: Exam, attempt: ExamAttempt | None, now: datetime) -> str:
    if attempt is not None:
        return "in_progress" if attempt.status == Status.IN_PROGRESS else "completed"
    return "available" if exam.is_open(now) else "unavailable"


def _question_counts(exams: list[Exam]) -> dict[UUID, dict[str, int]]:
    rows = (
        Question.objects.filter(exam__in=exams)
        .order_by()  # drop the default ordering so that it doesn't split the GROUP BY
        .values("exam_id", "subject")
        .annotate(count=Count("pk"))
    )
    counts: dict[UUID, dict[str, int]] = {}
    for row in rows:
        counts.setdefault(row["exam_id"], {})[row["subject"]] = row["count"]
    return counts


def _sections(exam: Exam, counts: dict[str, int]) -> list[SectionInfo]:
    return [
        SectionInfo(section.subject, section.title, counts.get(section.subject, 0))
        for section in exam.sections.all()
    ]


def _average(values: list[float]) -> float | None:
    """None, not 0, while there is no data: the contract says scores are never fabricated."""
    return sum(values) / len(values) if values else None


def _subject_average(results: list[ExamResult], subject: str) -> float | None:
    return _average(
        [
            item["percent"]
            for result in results
            for item in result.subjects
            if item["subject"] == subject
        ]
    )
