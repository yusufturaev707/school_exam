from apps.accounts.models import Pupil

from .models import Category, DailyQuestionAnswer, Game, GameSession
from .services import DAILY_QUESTION_POINTS

CATEGORY_DESCRIPTIONS = {
    Category.MEMORY: "Eslab qolish va diqqatni jamlash",
    Category.LOGIC: "Naqsh va qonuniyatlarni topish",
    Category.MATH: "Sonlar bilan aqlli o‘yinlar",
    Category.ATTENTION: "Kuzatuvchanlik va farqlarni ko‘rish",
    Category.SPATIAL: "Yo‘l topish va rejalashtirish",
    Category.LANGUAGE: "So‘z boyligi va harflar",
}


def categories_info() -> list[dict]:
    games = list(Game.objects.only("category", "is_active"))
    return [
        {
            "id": category.value,
            "title": category.label,
            "description": CATEGORY_DESCRIPTIONS[category],
            "game_count": sum(1 for game in games if game.category == category),
            "active_count": sum(1 for g in games if g.category == category and g.is_active),
        }
        for category in Category
    ]


def statistics_for(pupil: Pupil) -> dict:
    done = list(
        pupil.game_sessions.filter(status=GameSession.Status.COMPLETED)
        .select_related("game")
        .defer("content", "answers")
        .order_by("-completed_at")
    )
    correct_daily_answers = DailyQuestionAnswer.objects.filter(pupil=pupil, correct=True)
    return {
        "total_completed": len(done),
        # Every star the pupil earned; this is the number shown in the app header.
        "total_score": (
            sum(session.score + session.bonus for session in done)
            + correct_daily_answers.count() * DAILY_QUESTION_POINTS
        ),
        "categories": [
            {
                "category": category.value,
                "completed": sum(1 for s in done if s.game.category == category),
            }
            for category in Category
        ],
        "games": [_game_statistics(game, done) for game in Game.objects.filter(is_active=True)],
        "recent": done[:10],
    }


def _game_statistics(game: Game, done: list[GameSession]) -> dict:
    mine = [session for session in done if session.game_id == game.pk]
    # Best means highest share of the maximum, because levels have different maximum scores.
    best = max(mine, key=lambda s: s.score / (s.max_score or 1), default=None)
    return {
        "game_id": game.pk,
        "slug": game.slug,
        "title": game.title,
        "category": game.category,
        "completed": len(mine),
        "best_score": best.score if best else None,
        "max_score": best.max_score if best else None,
    }
