from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.accounts.models import Pupil
from apps.core.models import UUIDModel

from .generators import GENERATORS


class Category(models.TextChoices):
    MEMORY = "memory", "Xotira"
    LOGIC = "logic", "Mantiq"
    MATH = "math", "Matematika"
    ATTENTION = "attention", "Diqqat"
    SPATIAL = "spatial", "Fazoviy fikrlash"
    LANGUAGE = "language", "So‘z va til"


class Difficulty(models.TextChoices):
    EASY = "easy", "Oson"
    MEDIUM = "medium", "O‘rta"
    HARD = "hard", "Qiyin"


class GameKind(models.TextChoices):
    """Tells the frontend which engine renders the game."""

    MEMORY = "memory", "Xotira kartalari"
    MISSING_NUMBER = "missing-number", "Yashiringan son"
    PATTERN = "pattern", "Naqsh ustasi"
    ODD_ONE_OUT = "odd-one-out", "Ortiqchasini top"
    QUICK_MATH = "quick-math", "Tez hisob"
    MAZE = "maze", "Labirint"
    WORD_SEARCH = "word-search", "So‘zlar qidiruvi"


def validate_difficulties(value) -> None:
    if not isinstance(value, list) or not value or not set(value) <= set(Difficulty.values):
        raise ValidationError(f"Daraja ro‘yxati noto‘g‘ri. Mumkin: {Difficulty.values}")


class Game(UUIDModel):
    """Catalogue entry. The copy is here so admins can edit it without a frontend release."""

    slug = models.SlugField(unique=True)
    kind = models.CharField(max_length=20, choices=GameKind.choices)
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices)
    difficulties = models.JSONField(default=list, validators=[validate_difficulties])
    duration_minutes = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=False)
    intro_title = models.CharField(max_length=200)
    intro_text = models.CharField(max_length=500)
    instructions = models.JSONField(default=list, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "O‘yin"
        verbose_name_plural = "O‘yinlar"

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        if self.is_active and self.kind not in GENERATORS:
            raise ValidationError({"is_active": "Bu o‘yin turi uchun generator hali yozilmagan."})


class GameSession(UUIDModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Davom etmoqda"
        COMPLETED = "completed", "Yakunlangan"
        ABANDONED = "abandoned", "Tark etilgan"

    pupil = models.ForeignKey(Pupil, on_delete=models.CASCADE, related_name="game_sessions")
    game = models.ForeignKey(Game, on_delete=models.PROTECT, related_name="sessions")
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices)
    is_daily = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    # Generated content INCLUDING correct answers. Send only through `services.public_content`.
    content = models.JSONField()
    # {question_id: {"option_id": str, "correct": bool}}
    answers = models.JSONField(default=dict, blank=True)
    moves = models.PositiveIntegerField(null=True, blank=True)
    score = models.PositiveIntegerField(default=0)
    bonus = models.PositiveIntegerField(default=0)  # daily stars, kept apart for the result screen
    max_score = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    new_achievement_ids = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "O‘yin sessiyasi"
        verbose_name_plural = "O‘yin sessiyalari"
        indexes = [
            models.Index(fields=["pupil", "status"]),
            models.Index(fields=["status", "started_at"]),  # for purging stale sessions
        ]

    def __str__(self) -> str:
        return f"{self.pupil} / {self.game}"


class DailyChallengeCompletion(models.Model):
    """Its unique constraint is what guarantees one bonus a day, even for parallel sessions."""

    pupil = models.ForeignKey(Pupil, on_delete=models.CASCADE, related_name="+")
    date = models.DateField()
    session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name="+")
    completed_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pupil", "date"], name="one_daily_challenge_per_day")
        ]

    def __str__(self) -> str:
        return f"{self.pupil}: {self.date}"


class DailyQuestion(UUIDModel):
    prompt = models.CharField(max_length=200)
    sequence = models.CharField(max_length=200)
    options = models.JSONField(default=list)  # list of option labels
    correct_option = models.CharField(max_length=100, help_text="Ro‘yxatdagi to‘g‘ri variant.")
    explanation = models.CharField(max_length=500)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "Kun savoli"
        verbose_name_plural = "Kun savollari"

    def __str__(self) -> str:
        return f"{self.prompt} {self.sequence}"

    def clean(self) -> None:
        if self.correct_option not in (self.options or []):
            raise ValidationError({"correct_option": "To‘g‘ri javob ro‘yxatda bo‘lishi kerak."})

    def option_id(self, index: int) -> str:
        return f"{self.pk}-o{index + 1}"

    @property
    def correct_option_id(self) -> str:
        return self.option_id(self.options.index(self.correct_option))


class DailyQuestionAnswer(models.Model):
    """Its unique constraint is what makes "only the first answer of the day counts" a guarantee."""

    pupil = models.ForeignKey(Pupil, on_delete=models.CASCADE, related_name="+")
    date = models.DateField()
    question = models.ForeignKey(DailyQuestion, on_delete=models.CASCADE, related_name="+")
    option_id = models.CharField(max_length=60)
    correct = models.BooleanField()
    answered_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pupil", "date"], name="one_daily_answer_per_day")
        ]

    def __str__(self) -> str:
        return f"{self.pupil}: {self.date}"
