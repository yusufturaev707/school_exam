"""
Brain-game rules. Scores are computed only here, never accepted from the client, and rewards are
given once. As in the exams app, every write locks the session row, so double taps and retries
can't produce a second reward.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from random import Random
from uuid import UUID

from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.accounts.models import Pupil
from apps.core.exceptions import ApiError

from .achievements import unlocked_ids
from .generators import GENERATORS, replay_memory
from .models import (
    DailyChallengeCompletion,
    DailyQuestion,
    DailyQuestionAnswer,
    Difficulty,
    Game,
    GameSession,
)

POINTS_PER_CORRECT = 10
DAILY_BONUS = 20  # extra stars for finishing today's challenge, once a day
DAILY_QUESTION_POINTS = 5
# Which level the daily challenge uses, by day: more medium days than easy or hard ones.
DAILY_DIFFICULTY_CYCLE = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.MEDIUM, Difficulty.HARD]
STALE_SESSION_AGE = timedelta(days=1)

Status = GameSession.Status


def games_with_counts(pupil: Pupil) -> QuerySet[Game]:
    """
    `completed_count` is only ever this pupil's own number, never other pupils' data.
    The explicit order_by is required: Django ignores Meta.ordering once a query has GROUP BY,
    and the daily challenge picks a game by its position in this list.
    """
    return Game.objects.annotate(
        completed_count=Count(
            "sessions",
            filter=Q(sessions__pupil=pupil, sessions__status=Status.COMPLETED),
        )
    ).order_by("order", "slug")


# --------------------------------------------------------------------------- sessions


@dataclass(frozen=True)
class AnswerVerdict:
    question_id: str
    correct: bool
    correct_option_id: str
    explanation: str
    score: int
    correct_answers: int


def start_game(
    pupil: Pupil, game_id: UUID, difficulty: str | None, wants_daily: bool
) -> GameSession:
    game = Game.objects.filter(pk=game_id).first()
    if game is None:
        raise ApiError(404, "GAME_NOT_FOUND")
    generate = GENERATORS.get(game.kind)
    if not game.is_active or generate is None:
        raise ApiError(409, "GAME_NOT_AVAILABLE")

    difficulty = difficulty or game.difficulties[0]
    if difficulty not in game.difficulties:
        raise ApiError(422, "INVALID_DIFFICULTY")

    content = generate(Random(), difficulty)
    total = content["pairs"] if content["kind"] == "memory" else len(content["questions"])
    return GameSession.objects.create(
        pupil=pupil,
        game=game,
        difficulty=difficulty,
        is_daily=wants_daily and _qualifies_as_daily(pupil, game, difficulty),
        started_at=timezone.now(),
        content=content,
        total_questions=total,
        max_score=total * POINTS_PER_CORRECT,
    )


def answer_question(
    pupil: Pupil, session_id: UUID, question_id: str, option_id: str
) -> AnswerVerdict:
    with transaction.atomic():
        session = _lock_own_session(pupil, session_id)
        if session.content["kind"] == "memory":
            raise ApiError(400, "ANSWERS_NOT_SUPPORTED")

        question = next((q for q in session.content["questions"] if q["id"] == question_id), None)
        if question is None or option_id not in {o["id"] for o in question["options"]}:
            raise ApiError(422, "INVALID_ANSWER")

        # The first answer counts. A retry of it just gets the stored verdict back.
        if question_id not in session.answers:
            _ensure_in_progress(session)
            correct = option_id == question["correct_option_id"]
            session.answers[question_id] = {"option_id": option_id, "correct": correct}
            if correct:
                session.correct_answers += 1
                session.score += POINTS_PER_CORRECT  # wrong answers give 0, never negative
            session.save(update_fields=["answers", "correct_answers", "score"])

    return AnswerVerdict(
        question_id=question_id,
        correct=session.answers[question_id]["correct"],
        correct_option_id=question["correct_option_id"],
        explanation=question["explanation"],
        score=session.score,
        correct_answers=session.correct_answers,
    )


def complete_game(pupil: Pupil, session_id: UUID, moves) -> GameSession:
    """Idempotent: repeating it returns the same session and gives no second reward."""
    with transaction.atomic():
        session = _lock_own_session(pupil, session_id)
        if session.status == Status.COMPLETED:
            return session
        _ensure_in_progress(session)

        if session.content["kind"] == "memory":
            replay = replay_memory(session.content["cards"], moves)
            if not replay.valid:
                raise ApiError(422, "INVALID_MOVES", "Move log does not solve this board")
            session.moves = replay.moves
            session.correct_answers = replay.matched_pairs
            # Finishing is what counts: no penalties for time or the number of moves.
            session.score = replay.matched_pairs * POINTS_PER_CORRECT

        unlocked_before = unlocked_ids(pupil)
        session.status = Status.COMPLETED
        session.completed_at = timezone.now()
        session.save()

        if session.is_daily:
            _record_daily_completion(session)

        session.new_achievement_ids = sorted(unlocked_ids(pupil) - unlocked_before)
        session.save(update_fields=["new_achievement_ids", "bonus"])
    return session


def abandon_game(pupil: Pupil, session_id: UUID) -> GameSession:
    with transaction.atomic():
        session = _lock_own_session(pupil, session_id)
        if session.status == Status.IN_PROGRESS:  # a completed session stays completed
            session.status = Status.ABANDONED
            session.save(update_fields=["status"])
    return session


def own_session(pupil: Pupil, session_id: UUID) -> GameSession:
    session = GameSession.objects.select_related("game").filter(pk=session_id, pupil=pupil)
    return _found(session.first())


def resumable_session(pupil: Pupil, session_id: UUID) -> GameSession:
    session = own_session(pupil, session_id)
    _ensure_in_progress(session)
    return session


def finished_session(pupil: Pupil, session_id: UUID) -> GameSession:
    session = own_session(pupil, session_id)
    if session.status != Status.COMPLETED:
        raise ApiError(409, "SESSION_NOT_COMPLETED")
    return session


def public_content(content: dict) -> dict:
    """What the client may see. Correct answers and explanations are removed."""
    if content["kind"] == "memory":
        return content  # practice game: the board isn't secret, and the replay verifies the result
    questions = [
        {"id": q["id"], "sequence": q["sequence"], "options": q["options"]}
        for q in content["questions"]
    ]
    return {"kind": content["kind"], "questions": questions}


def answered_questions(session: GameSession) -> list[dict]:
    """For resuming: only questions already answered reveal their solution."""
    questions = session.content.get("questions", [])
    return [
        {
            "question_id": q["id"],
            "option_id": session.answers[q["id"]]["option_id"],
            "correct": session.answers[q["id"]]["correct"],
            "correct_option_id": q["correct_option_id"],
            "explanation": q["explanation"],
        }
        for q in questions
        if q["id"] in session.answers
    ]


def purge_stale_sessions() -> int:
    """Removes sessions nobody finished. Completed sessions are history and are kept."""
    stale = GameSession.objects.exclude(status=Status.COMPLETED).filter(
        started_at__lt=timezone.now() - STALE_SESSION_AGE
    )
    return stale.delete()[0]


def _lock_own_session(pupil: Pupil, session_id: UUID) -> GameSession:
    session = GameSession.objects.select_for_update().filter(pk=session_id, pupil=pupil)
    return _found(session.first())


def _found(session: GameSession | None) -> GameSession:
    if session is None:
        # 404 and not 403, so that the existence of another pupil's session isn't revealed.
        raise ApiError(404, "SESSION_NOT_FOUND")
    return session


def _ensure_in_progress(session: GameSession) -> None:
    if session.status == Status.COMPLETED:
        raise ApiError(409, "SESSION_COMPLETED")
    if session.status == Status.ABANDONED:
        raise ApiError(409, "SESSION_ABANDONED")


# --------------------------------------------------------------------------- daily challenge


@dataclass(frozen=True)
class DailyChallenge:
    date: date
    game: Game
    difficulty: str
    completed_at: datetime | None
    bonus: int = DAILY_BONUS


def daily_challenge(pupil: Pupil) -> DailyChallenge:
    """The same game and level for everybody on a given Tashkent calendar day."""
    today = timezone.localdate()
    games = list(games_with_counts(pupil).filter(is_active=True))
    if not games:
        raise ApiError(404, "DAILY_CHALLENGE_NOT_AVAILABLE")
    game = games[today.toordinal() % len(games)]

    difficulty = DAILY_DIFFICULTY_CYCLE[today.toordinal() % len(DAILY_DIFFICULTY_CYCLE)].value
    if difficulty not in game.difficulties:  # an admin may have narrowed this game's levels
        difficulty = game.difficulties[0]

    completion = DailyChallengeCompletion.objects.filter(pupil=pupil, date=today).first()
    return DailyChallenge(
        date=today,
        game=game,
        difficulty=difficulty,
        completed_at=completion.completed_at if completion else None,
    )


def confirm_daily_challenge(pupil: Pupil, session_id: UUID) -> DailyChallengeCompletion:
    """The explicit form from the contract; completing a daily session already records it."""
    with transaction.atomic():
        session = _lock_own_session(pupil, session_id)
        if not session.is_daily or session.status != Status.COMPLETED:
            raise ApiError(409, "NOT_A_COMPLETED_DAILY_SESSION")
        return _record_daily_completion(session)


def _qualifies_as_daily(pupil: Pupil, game: Game, difficulty: str) -> bool:
    today = daily_challenge(pupil)
    return (
        today.game.pk == game.pk and today.difficulty == difficulty and today.completed_at is None
    )


def _record_daily_completion(session: GameSession) -> DailyChallengeCompletion:
    """
    Counted on the day the session started, so finishing just after midnight still counts.
    Two parallel daily sessions can't both earn the bonus: the unique constraint lets only one
    `get_or_create` actually create the row.
    """
    completion, created = DailyChallengeCompletion.objects.get_or_create(
        pupil_id=session.pupil_id,
        date=timezone.localdate(session.started_at),
        defaults={"session": session, "completed_at": session.completed_at},
    )
    if created:
        session.bonus = DAILY_BONUS
    return completion


# --------------------------------------------------------------------------- question of the day


@dataclass(frozen=True)
class DailyQuestionState:
    date: date
    question: DailyQuestion
    answer: DailyQuestionAnswer | None


def daily_question_state(pupil: Pupil) -> DailyQuestionState:
    today = timezone.localdate()
    answer = (
        DailyQuestionAnswer.objects.select_related("question")
        .filter(pupil=pupil, date=today)
        .first()
    )
    # Once answered, keep showing that question even if an admin edits the list during the day.
    question = answer.question if answer else _question_of_the_day(today)
    return DailyQuestionState(date=today, question=question, answer=answer)


def answer_daily_question(
    pupil: Pupil, question_id: str | None, option_id: str
) -> DailyQuestionState:
    state = daily_question_state(pupil)
    if state.answer is not None:
        return state  # only the first answer of the day counts; repeats return it

    question = state.question
    valid_ids = [question.option_id(i) for i in range(len(question.options))]
    if option_id not in valid_ids or question_id not in (None, str(question.pk)):
        raise ApiError(422, "INVALID_ANSWER")

    # `get_or_create` plus the unique constraint settles a double tap: the first one wins.
    DailyQuestionAnswer.objects.get_or_create(
        pupil=pupil,
        date=state.date,
        defaults={
            "question": question,
            "option_id": option_id,
            "correct": option_id == question.correct_option_id,
            "answered_at": timezone.now(),
        },
    )
    return daily_question_state(pupil)


def _question_of_the_day(today: date) -> DailyQuestion:
    questions = list(DailyQuestion.objects.filter(is_active=True))
    if not questions:
        raise ApiError(404, "DAILY_QUESTION_NOT_AVAILABLE")
    return questions[today.toordinal() % len(questions)]
