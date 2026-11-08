"""
The admin's own history ("Admin jurnali"): who changed what and when. Read-only.

Django's other tables (content types, permissions, sessions) are deliberately not in the admin:
they are internal, permissions are given on the user and group pages, and a hand edit there
breaks things quietly.
"""

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.utils.html import format_html


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(LogEntry)
class LogEntryAdmin(ReadOnlyAdmin):
    """Who changed what in the admin and when: the history behind every "Tarix" button."""

    list_display = ["action_time", "user", "content_type", "object_link", "action", "message"]
    list_filter = ["action_flag", "content_type", "user"]
    list_select_related = ["user", "content_type"]
    search_fields = ["object_repr", "change_message", "user__username"]
    date_hierarchy = "action_time"

    @admin.display(description="Amal", ordering="action_flag")
    def action(self, entry) -> str:
        return entry.get_action_flag_display()

    @admin.display(description="Yozuv", ordering="object_repr")
    def object_link(self, entry) -> str:
        url = entry.get_admin_url() if not entry.is_deletion() else ""
        return (
            format_html('<a href="{}">{}</a>', url, entry.object_repr) if url else entry.object_repr
        )

    @admin.display(description="O‘zgarish")
    def message(self, entry) -> str:
        return entry.get_change_message()
