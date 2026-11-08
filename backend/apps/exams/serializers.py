from rest_framework import serializers

from apps.core.serializers import RichContentField, UtcDateTimeField

from . import selectors
from .models import ExamResult

MAX_CLIENT_SEQ = 2**63 - 1  # upper limit of the BigIntegerField column

# ---------------------------------------------------------------------------- request bodies


class SaveAnswerSerializer(serializers.Serializer):
    selectedOptionIds = serializers.ListField(child=serializers.CharField())
    clientSeq = serializers.IntegerField(min_value=0, max_value=MAX_CLIENT_SEQ)


class UnsavedAnswerSerializer(SaveAnswerSerializer):
    questionId = serializers.CharField()


class SubmitSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=ExamResult.FinishReason.choices)
    unsavedAnswers = UnsavedAnswerSerializer(many=True, required=False, default=list)


# ---------------------------------------------------------------------------- exams and attempts


class SectionSerializer(serializers.Serializer):
    subject = serializers.CharField()
    title = serializers.CharField()
    questionCount = serializers.IntegerField(source="question_count")


class ExamSummarySerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    totalQuestions = serializers.IntegerField(source="total_questions")
    durationMinutes = serializers.IntegerField(source="duration_minutes")
    sections = SectionSerializer(many=True)
    status = serializers.CharField()
    activeAttemptId = serializers.CharField(source="active_attempt_id")
    resultId = serializers.CharField(source="result_id")
    availableFrom = UtcDateTimeField(source="available_from")


class OptionSerializer(serializers.Serializer):
    """No `is_correct` here. This is what keeps correct answers out of the exam payload."""

    id = serializers.CharField()
    label = serializers.CharField()
    content = RichContentField()


class QuestionSerializer(serializers.Serializer):
    """No `explanation` here for the same reason: it would give the answer away during the exam."""

    id = serializers.CharField()
    number = serializers.IntegerField()
    subject = serializers.CharField()
    type = serializers.CharField()
    prompt = RichContentField()
    passage = RichContentField(nullable=True)
    options = OptionSerializer(many=True)


class AttemptStateSerializer(serializers.Serializer):
    """Everything about an attempt except its questions: what the client re-checks every minute."""

    id = serializers.CharField(source="attempt.id")
    examId = serializers.CharField(source="attempt.exam_id")
    examTitle = serializers.CharField(source="attempt.exam.title")
    status = serializers.CharField(source="attempt.status")
    startedAt = UtcDateTimeField(source="attempt.started_at")
    expiresAt = UtcDateTimeField(source="attempt.expires_at")
    serverTime = UtcDateTimeField(source="server_time")
    sections = SectionSerializer(many=True)
    answers = serializers.JSONField()
    resultId = serializers.CharField(source="attempt.result_id")


class AttemptSessionSerializer(AttemptStateSerializer):
    questions = QuestionSerializer(many=True)


class SavedAnswerSerializer(serializers.Serializer):
    questionId = serializers.CharField(source="question_id")
    savedAt = UtcDateTimeField(source="saved_at")


class SubmitResultSerializer(serializers.Serializer):
    attemptId = serializers.CharField(source="id")
    status = serializers.CharField()
    resultId = serializers.CharField(source="result_id")


# ---------------------------------------------------------------------------- results


class ResultTotalsSerializer(serializers.Serializer):
    correct = serializers.IntegerField()
    incorrect = serializers.IntegerField()
    unanswered = serializers.IntegerField()
    total = serializers.IntegerField()
    score = serializers.IntegerField()
    maxScore = serializers.IntegerField(source="max_score")
    percent = serializers.FloatField()


class ReviewItemSerializer(serializers.Serializer):
    questionId = serializers.CharField(source="question_id")
    number = serializers.IntegerField()
    subject = serializers.CharField()
    prompt = RichContentField()
    passage = RichContentField(nullable=True)
    options = OptionSerializer(many=True)
    selectedOptionIds = serializers.JSONField(source="selected_option_ids")
    correctOptionIds = serializers.JSONField(source="correct_option_ids")
    explanation = RichContentField(nullable=True)


class ExamResultSerializer(serializers.Serializer):
    id = serializers.CharField()
    attemptId = serializers.CharField(source="attempt_id")
    examTitle = serializers.CharField(source="attempt.exam.title")
    completedAt = UtcDateTimeField(source="completed_at")
    finishReason = serializers.CharField(source="finish_reason")
    totals = ResultTotalsSerializer(source="*")
    subjects = serializers.JSONField()
    review = serializers.SerializerMethodField()

    def get_review(self, result: ExamResult) -> dict:
        # Exam policy decides this. When disabled, correct answers must not be sent at all.
        if not result.attempt.exam.review_enabled:
            return {"enabled": False}
        items = selectors.review_items(result)
        return {"enabled": True, "items": ReviewItemSerializer(items, many=True).data}


class ResultSummarySerializer(serializers.Serializer):
    id = serializers.CharField()
    examTitle = serializers.CharField(source="attempt.exam.title")
    completedAt = UtcDateTimeField(source="completed_at")
    correct = serializers.IntegerField()
    total = serializers.IntegerField()
    percent = serializers.FloatField()


# ---------------------------------------------------------------------------- dashboard


class RecentActivitySerializer(serializers.Serializer):
    resultId = serializers.CharField(source="id")
    examTitle = serializers.CharField(source="attempt.exam.title")
    completedAt = UtcDateTimeField(source="completed_at")
    correct = serializers.IntegerField()
    total = serializers.IntegerField()
    status = serializers.SerializerMethodField()

    def get_status(self, result: ExamResult) -> str:
        is_timeout = result.finish_reason == ExamResult.FinishReason.TIMEOUT
        return "expired" if is_timeout else "completed"


class DashboardPupilSerializer(serializers.Serializer):
    firstName = serializers.CharField(source="first_name")


class SubjectPercentSerializer(serializers.Serializer):
    subject = serializers.CharField()
    percent = serializers.FloatField()


class DashboardStatsSerializer(serializers.Serializer):
    totalExams = serializers.IntegerField(source="total_exams")
    completedExams = serializers.IntegerField(source="completed_exams")
    overallPercent = serializers.FloatField(source="overall_percent")
    subjects = SubjectPercentSerializer(many=True)


class DashboardSerializer(serializers.Serializer):
    student = DashboardPupilSerializer(source="pupil")
    examinations = ExamSummarySerializer(many=True)
    stats = DashboardStatsSerializer()
    recentActivity = RecentActivitySerializer(source="recent_activity", many=True)
