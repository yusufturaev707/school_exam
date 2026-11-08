"""
Achievements reward participation and exploration only: no streaks, no "play every day" pressure.

They are computed from a pupil's history rather than stored, so a stored value can never go out
of sync with what actually happened. Rules live in code because each one is a piece of logic.

A rule's `events` function returns the moments that counted as progress, in time order.
Progress is how many there are, and the badge unlocks at the `target`-th one.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from apps.accounts.models import Pupil

from .models import Category, DailyChallengeCompletion, Game, GameSession

Sessions = list[GameSession]


def _all_completions(done: Sessions, _daily: list[datetime]) -> list[datetime]:
    return [session.completed_at for session in done]


def _completions_in(category: str):
    def events(done: Sessions, _daily: list[datetime]) -> list[datetime]:
        return [s.completed_at for s in done if s.game.category == category]

    return events


def _new_categories(done: Sessions, _daily: list[datetime]) -> list[datetime]:
    first_seen: dict[str, datetime] = {}
    for session in done:
        first_seen.setdefault(session.game.category, session.completed_at)
    return list(first_seen.values())


def _daily_completions(_done: Sessions, daily: list[datetime]) -> list[datetime]:
    return daily


@dataclass(frozen=True)
class AchievementRule:
    id: str
    title: str
    description: str
    icon: str
    target: int
    events: Callable[[Sessions, list[datetime]], list[datetime]]
    # When no active game in this category exists yet, the badge is "coming soon", not a task.
    category: str | None = None


RULES = [
    AchievementRule(
        "first-step",
        "Birinchi qadam",
        "Birinchi o‘yinni yakunla.",
        "footprints",
        1,
        _all_completions,
    ),
    AchievementRule(
        "memory-master",
        "Xotira ustasi",
        "Xotira o‘yinini yakunla.",
        "brain",
        1,
        _completions_in(Category.MEMORY),
        Category.MEMORY,
    ),
    AchievementRule(
        "math-explorer",
        "Matematik izquvar",
        "3 ta matematika o‘yinini yakunla.",
        "calculator",
        3,
        _completions_in(Category.MATH),
        Category.MATH,
    ),
    AchievementRule(
        "logic-thinker",
        "Mantiqiy fikrlovchi",
        "3 ta mantiq o‘yinini yakunla.",
        "puzzle",
        3,
        _completions_in(Category.LOGIC),
        Category.LOGIC,
    ),
    AchievementRule(
        "attention-champion",
        "Diqqat chempioni",
        "Diqqat o‘yinini yakunla.",
        "eye",
        1,
        _completions_in(Category.ATTENTION),
        Category.ATTENTION,
    ),
    AchievementRule(
        "curious-mind",
        "Izlanuvchan bola",
        "3 xil yo‘nalishdagi o‘yinlarni sinab ko‘r.",
        "compass",
        3,
        _new_categories,
    ),
    AchievementRule(
        "daily-explorer",
        "Kun kashfiyotchisi",
        "Bugungi intellektual topshiriqni bajar.",
        "sun",
        1,
        _daily_completions,
    ),
]


@dataclass(frozen=True)
class Achievement:
    id: str
    title: str
    description: str
    icon: str
    unlocked_at: datetime | None
    progress_current: int
    progress_target: int
    coming_soon: bool


def achievements_for(pupil: Pupil) -> list[Achievement]:
    done = list(
        pupil.game_sessions.filter(status=GameSession.Status.COMPLETED)
        .select_related("game")
        .defer("content", "answers")  # large JSON that isn't needed here
        .order_by("completed_at")
    )
    daily = list(
        DailyChallengeCompletion.objects.filter(pupil=pupil)
        .order_by("completed_at")
        .values_list("completed_at", flat=True)
    )
    active_categories = set(Game.objects.filter(is_active=True).values_list("category", flat=True))

    achievements = []
    for rule in RULES:
        events = rule.events(done, daily)
        unlocked_at = events[rule.target - 1] if len(events) >= rule.target else None
        achievements.append(
            Achievement(
                id=rule.id,
                title=rule.title,
                description=rule.description,
                icon=rule.icon,
                unlocked_at=unlocked_at,
                progress_current=min(rule.target, len(events)),
                progress_target=rule.target,
                coming_soon=(
                    unlocked_at is None
                    and rule.category is not None
                    and rule.category not in active_categories
                ),
            )
        )
    return achievements


def unlocked_ids(pupil: Pupil) -> set[str]:
    return {a.id for a in achievements_for(pupil) if a.unlocked_at is not None}
