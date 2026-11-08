"""
Django's own tables in the admin, so the sidebar lists every table in the database. All of them
are read-only: they are written by Django itself, and a hand edit there breaks things quietly.
"""

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.utils.html import format_html

from apps.accounts.authentication import SESSION_PUPIL_KEY
from apps.accounts.models import Pupil


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


@admin.register(Permission)
class PermissionAdmin(ReadOnlyAdmin):
    """Created by Django for every model; given to users and groups on their own pages."""

    list_display = ["name", "codename", "content_type"]
    list_filter = ["content_type__app_label"]
    list_select_related = ["content_type"]
    search_fields = ["name", "codename"]


@admin.register(ContentType)
class ContentTypeAdmin(ReadOnlyAdmin):
    list_display = ["app_label", "model", "name"]
    list_filter = ["app_label"]
    search_fields = ["app_label", "model"]
    ordering = ["app_label", "model"]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """
    Logged-in browsers, pupils' and staff's. Only superusers see this list, because a session key
    is as good as the password (it is in the page for the delete action). The stored data itself
    is never shown. Deleting a session logs that browser out.
    """

    list_display = ["short_key", "owner", "expire_date", "is_active"]
    list_display_links = None  # the detail page would add nothing
    fields = ["short_key", "owner", "expire_date", "is_active"]
    readonly_fields = fields
    list_per_page = 50
    ordering = ["-expire_date"]
    date_hierarchy = "expire_date"

    def has_module_permission(self, request) -> bool:
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None) -> bool:
        return request.user.is_superuser

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return request.user.is_superuser

    @admin.display(description="Kalit", ordering="session_key")
    def short_key(self, session) -> str:
        return f"{session.session_key[:6]}…"

    @admin.display(description="Kim")
    def owner(self, session) -> str:
        data = session.get_decoded()
        if data.get(SESSION_PUPIL_KEY):
            pupil = Pupil.objects.filter(pk=data[SESSION_PUPIL_KEY]).first()
            return f"O‘quvchi: {pupil}" if pupil else "O‘quvchi (o‘chirilgan)"
        if data.get("_auth_user_id"):
            user = get_user_model().objects.filter(pk=data["_auth_user_id"]).first()
            return f"Xodim: {user}" if user else "Xodim (o‘chirilgan)"
        return "—"

    @admin.display(description="Amalda", boolean=True)
    def is_active(self, session) -> bool:
        return session.expire_date > timezone.now()
