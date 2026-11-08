from rest_framework import serializers

from apps.core.serializers import UtcDateTimeField

from . import services
from .achievements import achievements_for
from .models import GameSession

# ---------------------------------------------------------------------------- request bodies


class StartGameSerializer(serializers.Serializer):
    difficulty = serializers.CharField(required=False)  # checked against the game's levels
    daily = serializers.BooleanField(required=False, default=False)


class AnswerSerializer(serializers.Serializer):
    questionId = serializers.CharField()
    optionId = serializers.CharField()


class DailyAnswerSerializer(serializers.Serializer):
    questionId = serializers.CharField(required=False)
    optionId = serializers.CharField()


class CompleteGameSerializer(serializers.Serializer):
    """`moves` keeps its raw shape on purpose: the memory replay validates it strictly itself."""

    moves = serializers.JSONField(required=False, default=None)


class ConfirmDailySerializer(serializers.Serializer):
    sessionId = serializers.UUIDField()


# ---------------------------------------------------------------------------- catalogue


class GameIntroSerializer(serializers.Serializer):
    title = serializers.CharField(source="intro_title")
    text = serializers.CharField(source="intro_text")


class GameSerializer(serializers.Serializer):
    id = serializers.CharField()
    slug = serializers.CharField()
    kind = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    difficulties = serializers.JSONField()
    durationMinutes = serializers.IntegerField(source="duration_minutes")
    isActive = serializers.BooleanField(source="is_active")
    intro = GameIntroSerializer(source="*")
    instructions = serializers.JSONField()
    completedCount = serializers.IntegerField(source="completed_count")


class CategorySerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    gameCount = serializers.IntegerField(source="game_count")
    activeCount = serializers.IntegerField(source="active_count")


# ---------------------------------------------------------------------------- sessions


class GameSessionSerializer(serializers.Serializer):
    id = serializers.CharField()
    gameId = serializers.CharField(source="game_id")
    gameSlug = serializers.CharField(source="game.slug")
    difficulty = serializers.CharField()
    isDaily = serializers.BooleanField(source="is_daily")
    startedAt = UtcDateTimeField(source="started_at")
    completedAt = UtcDateTimeField(source="completed_at")
    status = serializers.CharField()
    score = serializers.IntegerField()
    correctAnswers = serializers.IntegerField(source="correct_answers")
    totalQuestions = serializers.IntegerField(source="total_questions")


class StartedGameSerializer(serializers.Serializer):
    """The one way a session's content reaches the client, always via `public_content`."""

    session = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    def get_session(self, session: GameSession) -> dict:
        return GameSessionSerializer(session).data

    def get_content(self, session: GameSession) -> dict:
        return services.public_content(session.content)


class ResumeAnswerSerializer(serializers.Serializer):
    questionId = serializers.CharField(source="question_id")
    optionId = serializers.CharField(source="option_id")
    correct = serializers.BooleanField()
    correctOptionId = serializers.CharField(source="correct_option_id")
    explanation = serializers.CharField()


class ResumedGameSerializer(StartedGameSerializer):
    answers = serializers.SerializerMethodField()

    def get_answers(self, session: GameSession) -> list:
        return ResumeAnswerSerializer(services.answered_questions(session), many=True).data


class AnswerVerdictSerializer(serializers.Serializer):
    questionId = serializers.CharField(source="question_id")
    correct = serializers.BooleanField()
    correctOptionId = serializers.CharField(source="correct_option_id")
    explanation = serializers.CharField()
    score = serializers.IntegerField()
    correctAnswers = serializers.IntegerField(source="correct_answers")


# ---------------------------------------------------------------------------- achievements, results


class ProgressSerializer(serializers.Serializer):
    current = serializers.IntegerField(source="progress_current")
    target = serializers.IntegerField(source="progress_target")


class AchievementSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    icon = serializers.CharField()
    unlockedAt = UtcDateTimeField(source="unlocked_at")
    progress = ProgressSerializer(source="*")
    comingSoon = serializers.BooleanField(source="coming_soon")


class GameBriefSerializer(serializers.Serializer):
    id = serializers.CharField()
    slug = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()


class GameResultSerializer(serializers.Serializer):
    sessionId = serializers.CharField(source="id")
    game = GameBriefSerializer()
    difficulty = serializers.CharField()
    score = serializers.IntegerField()
    bonus = serializers.IntegerField()
    maxScore = serializers.IntegerField(source="max_score")
    correctAnswers = serializers.IntegerField(source="correct_answers")
    totalQuestions = serializers.IntegerField(source="total_questions")
    durationSeconds = serializers.SerializerMethodField()
    moves = serializers.IntegerField()
    completedAt = UtcDateTimeField(source="completed_at")
    isDaily = serializers.BooleanField(source="is_daily")
    newAchievements = serializers.SerializerMethodField()

    def get_durationSeconds(self, session: GameSession) -> int:
        return max(0, round((session.completed_at - session.started_at).total_seconds()))

    def get_newAchievements(self, session: GameSession) -> list:
        if not session.new_achievement_ids:
            return []
        new = [a for a in achievements_for(session.pupil) if a.id in session.new_achievement_ids]
        return AchievementSerializer(new, many=True).data


# ---------------------------------------------------------------------------- daily


class DailyChallengeSerializer(serializers.Serializer):
    date = serializers.CharField()
    game = GameSerializer()
    difficulty = serializers.CharField()
    completed = serializers.SerializerMethodField()
    completedAt = UtcDateTimeField(source="completed_at")
    bonus = serializers.IntegerField()

    def get_completed(self, challenge) -> bool:
        return challenge.completed_at is not None


class DailyQuestionStateSerializer(serializers.Serializer):
    date = serializers.CharField()
    question = serializers.SerializerMethodField()
    points = serializers.SerializerMethodField()
    answer = serializers.SerializerMethodField()

    def get_question(self, state: services.DailyQuestionState) -> dict:
        question = state.question
        return {
            "id": str(question.pk),
            "prompt": question.prompt,
            "sequence": question.sequence,
            # Only ids and labels: the correct option is never sent before the pupil answers.
            "options": [
                {"id": question.option_id(i), "label": label}
                for i, label in enumerate(question.options)
            ],
        }

    def get_points(self, state: services.DailyQuestionState) -> int:
        return services.DAILY_QUESTION_POINTS

    def get_answer(self, state: services.DailyQuestionState) -> dict | None:
        answer = state.answer
        if answer is None:
            return None
        return {
            "selectedOptionId": answer.option_id,
            "correct": answer.correct,
            "correctOptionId": state.question.correct_option_id,
            "explanation": state.question.explanation,
            "pointsEarned": services.DAILY_QUESTION_POINTS if answer.correct else 0,
            "answeredAt": UtcDateTimeField().to_representation(answer.answered_at),
        }


# ---------------------------------------------------------------------------- statistics


class CategoryStatSerializer(serializers.Serializer):
    category = serializers.CharField()
    completed = serializers.IntegerField()


class GameStatSerializer(serializers.Serializer):
    gameId = serializers.CharField(source="game_id")
    slug = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    completed = serializers.IntegerField()
    bestScore = serializers.IntegerField(source="best_score")
    maxScore = serializers.IntegerField(source="max_score")


class RecentGameSerializer(serializers.Serializer):
    sessionId = serializers.CharField(source="id")
    slug = serializers.CharField(source="game.slug")
    title = serializers.CharField(source="game.title")
    category = serializers.CharField(source="game.category")
    score = serializers.IntegerField()
    bonus = serializers.IntegerField()
    maxScore = serializers.IntegerField(source="max_score")
    completedAt = UtcDateTimeField(source="completed_at")


class StatisticsSerializer(serializers.Serializer):
    totalCompleted = serializers.IntegerField(source="total_completed")
    totalScore = serializers.IntegerField(source="total_score")
    categories = CategoryStatSerializer(many=True)
    games = GameStatSerializer(many=True)
    recent = RecentGameSerializer(many=True)
