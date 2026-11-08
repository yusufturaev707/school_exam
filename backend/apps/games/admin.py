from django.contrib import admin

from .models import (
    DailyChallengeCompletion,
    DailyQuestion,
    DailyQuestionAnswer,
    Game,
    GameSession,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Records the games write themselves: they are what the stars and bonuses are counted from."""

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "category", "is_active", "order"]
    list_filter = ["is_active", "category"]
    list_editable = ["order"]
    prepopulated_fields = {"slug": ["title"]}


@admin.register(DailyQuestion)
class DailyQuestionAdmin(admin.ModelAdmin):
    list_display = ["prompt", "sequence", "correct_option", "is_active", "order"]
    list_filter = ["is_active"]
    list_editable = ["order"]


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    """Read-only, and `content` is left out because it's bulky and contains the answers."""

    list_display = ["pupil", "game", "difficulty", "status", "score", "bonus", "started_at"]
    list_filter = ["status", "game", "difficulty"]
    list_select_related = ["pupil", "game"]
    search_fields = ["pupil__first_name", "pupil__last_name"]
    exclude = ["content", "answers"]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


@admin.register(DailyChallengeCompletion)
class DailyChallengeCompletionAdmin(ReadOnlyAdmin):
    list_display = ["pupil", "date", "session", "completed_at"]
    list_filter = ["date"]
    list_select_related = ["pupil", "session__game"]
    search_fields = ["pupil__first_name", "pupil__last_name"]
    date_hierarchy = "date"


@admin.register(DailyQuestionAnswer)
class DailyQuestionAnswerAdmin(ReadOnlyAdmin):
    list_display = ["pupil", "date", "question", "correct", "answered_at"]
    list_filter = ["correct", "date"]
    list_select_related = ["pupil", "question"]
    search_fields = ["pupil__first_name", "pupil__last_name"]
    date_hierarchy = "date"
