from django.contrib import admin

from .models import DailyQuestion, Game, GameSession


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
