"""
The results report in the admin: one exam's results, narrowed by the same filters as the result
list (place, finish reason, search), gathered into one plain dict.

The page, and every file it offers (JSON, Excel, PDF, PNG), is drawn from this one dict, so a
number never differs between what staff see on screen and what they download.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict

from django.utils import timezone

from .models import AttemptAnswer, Exam, ExamResult, Subject

# The hierarchy filters of the result list (apps.schools.filters), from the widest place down.
PLACE_LEVELS = [
    ("region", "Viloyat", "Viloyatlar"),
    ("district", "Tuman", "Tumanlar"),
    ("school", "Maktab", "Maktablar"),
    ("classroom", "Sinf", "Sinflar"),
]

# The same thresholds as the pupil's result page (frontend features/results/utils/feedback.ts).
BANDS = [
    ("high", "A’lo", 80, "80–100%"),
    ("mid", "Yaxshi", 50, "50–79%"),
    ("growing", "Mashq kerak", 0, "0–49%"),
]

FINISH_REASONS = dict(ExamResult.FinishReason.choices)
SUBJECT_NAMES = dict(Subject.choices)


def _round(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(value, digits)


def _band(percent: float) -> str:
    return next(code for code, _, low, _ in BANDS if percent >= low)


def _bucket(percent: float) -> int:
    return min(int(percent // 10), 9)


def _places(pupil) -> dict:
    classroom = pupil.classroom
    school = classroom.school
    district = school.district
    region = district.region
    graduated = f" ({classroom.graduated_year} bitiruvchilari)" if classroom.graduated_year else ""
    return {
        "region": (region.pk, region.name),
        "district": (district.pk, district.name),
        "school": (school.pk, school.name),
        "classroom": (classroom.pk, f"{classroom.name}{graduated}"),
    }


def group_level(chosen: dict[str, str]) -> int | None:
    """One level below the narrowest place chosen: no region → regions, a region → districts."""
    deepest = max(
        (index for index, (param, _, _) in enumerate(PLACE_LEVELS) if chosen.get(param)),
        default=-1,
    )
    return deepest + 1 if deepest + 1 < len(PLACE_LEVELS) else None


def build_report(exam: Exam, results, *, chosen: dict[str, str], filters: list[dict]) -> dict:
    """
    `results` is the result list's filtered queryset, limited to `exam`. `chosen` holds the place
    filters from the URL (region, district, ...); `filters` describes all of them for people.
    """
    results = list(
        results.select_related("attempt__pupil__classroom__school__district__region").order_by(
            "-score", "attempt__pupil__last_name", "attempt__pupil__first_name"
        )
    )
    sections = {section.subject: section.title for section in exam.sections.all()}
    questions = list(exam.questions.prefetch_related("options").order_by("number"))
    subject_codes = [code for code in Subject.values if any(q.subject == code for q in questions)]
    max_score = len(questions) * exam.points_per_question

    pupils = []
    rank, previous = 0, None
    for position, result in enumerate(results, start=1):
        attempt = result.attempt
        if result.score != previous:  # equal scores share a place: 1, 2, 2, 4
            rank, previous = position, result.score
        places = _places(attempt.pupil)
        duration = (result.completed_at - attempt.started_at).total_seconds() / 60
        pupils.append(
            {
                "rank": rank,
                "name": str(attempt.pupil),
                "region": places["region"][1],
                "district": places["district"][1],
                "school": places["school"][1],
                "classroom": places["classroom"][1],
                "correct": result.correct,
                "incorrect": result.incorrect,
                "unanswered": result.unanswered,
                "total": result.total,
                "score": result.score,
                "maxScore": result.max_score,
                "percent": _round(result.percent),
                "band": _band(_round(result.percent)),
                "subjects": {item["subject"]: _round(item["percent"]) for item in result.subjects},
                "finishReason": FINISH_REASONS.get(result.finish_reason, result.finish_reason),
                "startedAt": timezone.localtime(attempt.started_at).isoformat(timespec="seconds"),
                "completedAt": timezone.localtime(result.completed_at).isoformat(
                    timespec="seconds"
                ),
                "durationMinutes": _round(max(duration, 0)),
                "_places": places,
            }
        )

    # Rounded as shown, so 79.96% is counted where people see it: among the 80% ones.
    percents = [pupil["percent"] for pupil in pupils]
    report = {
        "exam": {
            "id": str(exam.pk),
            "title": exam.title,
            "durationMinutes": exam.duration_minutes,
            "questionCount": len(questions),
            "pointsPerQuestion": exam.points_per_question,
            "maxScore": max_score,
        },
        "filters": filters,
        "generatedAt": timezone.localtime().isoformat(timespec="seconds"),
        "summary": _summary(results, percents, pupils),
        "distribution": _distribution(percents),
        "bands": [
            {
                "code": code,
                "label": label,
                "range": shown,
                "count": sum(1 for pupil in pupils if pupil["band"] == code),
            }
            for code, label, _, shown in BANDS
        ],
        "subjects": _subjects(results, subject_codes, sections),
        "groups": _groups(pupils, group_level(chosen)),
        "questions": _questions(questions, results, sections),
        "subjectColumns": [
            {"code": code, "name": sections.get(code) or SUBJECT_NAMES[code]}
            for code in subject_codes
        ],
        "pupils": pupils,
    }
    for pupil in pupils:
        del pupil["_places"]
    return report


def _summary(results, percents: list[float], pupils: list[dict]) -> dict:
    if not results:
        return {"count": 0}
    durations = [pupil["durationMinutes"] for pupil in pupils]
    reasons = Counter(result.finish_reason for result in results)
    return {
        "count": len(results),
        "averagePercent": _round(statistics.fmean(percents)),
        "medianPercent": _round(statistics.median(percents)),
        "maxPercent": _round(max(percents)),
        "minPercent": _round(min(percents)),
        "stdevPercent": _round(statistics.pstdev(percents)),
        "averageScore": _round(statistics.fmean(result.score for result in results)),
        "averageCorrect": _round(statistics.fmean(result.correct for result in results)),
        "averageDurationMinutes": _round(statistics.fmean(durations)),
        "finishedManually": reasons.get(ExamResult.FinishReason.MANUAL, 0),
        "finishedByTimeout": reasons.get(ExamResult.FinishReason.TIMEOUT, 0),
    }


def _distribution(percents: list[float]) -> list[dict]:
    counts = Counter(_bucket(percent) for percent in percents)
    return [
        {
            "from": index * 10,
            "to": 100 if index == 9 else index * 10 + 9,
            "label": "90–100" if index == 9 else f"{index * 10}–{index * 10 + 9}",
            "count": counts.get(index, 0),
        }
        for index in range(10)
    ]


def _subjects(results, subject_codes: list[str], sections: dict) -> list[dict]:
    totals = {
        code: {"correct": 0, "incorrect": 0, "unanswered": 0, "total": 0} for code in subject_codes
    }
    for result in results:
        for item in result.subjects:
            stats = totals.setdefault(
                item["subject"], {"correct": 0, "incorrect": 0, "unanswered": 0, "total": 0}
            )
            for key in stats:
                stats[key] += item.get(key, 0)
    return [
        {
            "subject": code,
            "name": sections.get(code) or SUBJECT_NAMES.get(code, code),
            **stats,
            "averagePercent": _round(stats["correct"] / stats["total"] * 100)
            if stats["total"]
            else None,
        }
        for code, stats in totals.items()
    ]


def _groups(pupils: list[dict], level: int | None) -> dict | None:
    if level is None:
        return None
    param, label, plural = PLACE_LEVELS[level]
    grouped: dict = defaultdict(list)
    for pupil in pupils:
        grouped[pupil["_places"][param]].append(pupil)
    rows = []
    for (pk, name), members in grouped.items():
        percents = [member["percent"] for member in members]
        rows.append(
            {
                "id": pk,
                "name": name,
                "count": len(members),
                "averagePercent": _round(statistics.fmean(percents)),
                "maxPercent": max(percents),
                "minPercent": min(percents),
                "averageScore": _round(statistics.fmean(member["score"] for member in members)),
                "high": sum(1 for member in members if member["band"] == "high"),
            }
        )
    rows.sort(key=lambda row: (-row["averagePercent"], row["name"]))
    return {"param": param, "label": label, "title": plural, "rows": rows}


def _questions(questions, results, sections: dict) -> list[dict]:
    """
    How each question went, by the current answer key. With shuffling a question has another
    number and other letters for every pupil, so it is shown by its number and letters in the exam.
    """
    attempt_ids = [result.attempt_id for result in results]
    picks: dict = defaultdict(Counter)
    for question_id, selected in (
        AttemptAnswer.objects.filter(attempt_id__in=attempt_ids)
        .values_list("question_id", "selected_option_ids")
        .iterator(chunk_size=5000)
    ):
        for option_id in selected or []:
            picks[question_id][option_id] += 1
    answered_by: dict = Counter(
        AttemptAnswer.objects.filter(attempt_id__in=attempt_ids)
        .exclude(selected_option_ids=[])
        .values_list("question_id", flat=True)
        .iterator(chunk_size=5000)
    )

    count = len(results)
    rows = []
    for question in questions:
        options = list(question.options.all())
        chosen = picks.get(question.pk, Counter())
        correct_ids = {str(option.pk) for option in options if option.is_correct}
        # Single choice: one option per pupil, so the right option's count is the right answers.
        correct = sum(chosen.get(option_id, 0) for option_id in correct_ids)
        answered = answered_by.get(question.pk, 0)
        rows.append(
            {
                "number": question.number,
                "subject": question.subject,
                "subjectName": sections.get(question.subject)
                or SUBJECT_NAMES.get(question.subject, question.subject),
                "difficulty": question.get_difficulty_display() if question.difficulty else "",
                "correct": correct,
                "incorrect": max(answered - correct, 0),
                "unanswered": max(count - answered, 0),
                "correctPercent": _round(correct / count * 100) if count else None,
                "options": [
                    {
                        "label": option.label,
                        "count": chosen.get(str(option.pk), 0),
                        "isCorrect": option.is_correct,
                    }
                    for option in options
                ],
            }
        )
    return rows
