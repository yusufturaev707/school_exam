import csv
import re

import segno
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe

from apps.schools.filters import graduated_filter, hierarchy_filters

from .models import Pupil, QrLoginToken, hash_imie
from .services import issue_qr_tokens, qr_payload

# One print run. A bigger page gets slow to render and to print; do it class by class instead.
MAX_QR_TICKETS = 1000


class PupilAdminForm(forms.ModelForm):
    """IMIE (JSHSHIR) can be written here but never read back: only its hash is stored."""

    imie = forms.RegexField(
        regex=r"^\d{14}$",
        required=False,
        label="JSHSHIR (IMIE)",
        help_text="14 ta raqam. Saqlangach ko‘rsatilmaydi; o‘zgartirish uchun yangisini kiriting.",
    )

    class Meta:
        model = Pupil
        fields = ["classroom", "last_name", "first_name", "middle_name", "photo_url", "status"]

    def clean(self):
        cleaned = super().clean()
        imie = cleaned.get("imie")
        if not imie:
            if not self.instance.imie_hash and "imie" not in self.errors:
                self.add_error("imie", "Yangi o‘quvchi uchun JSHSHIR majburiy.")
            return cleaned
        duplicate = Pupil.objects.filter(imie_hash=hash_imie(imie))
        if duplicate.exclude(pk=self.instance.pk).exists():
            self.add_error("imie", "Bu JSHSHIR boshqa o‘quvchiga tegishli.")
        return cleaned

    def save(self, commit=True):
        if self.cleaned_data.get("imie"):
            self.instance.set_imie(self.cleaned_data["imie"])
        return super().save(commit)


def qr_lifetime_choices() -> list[tuple[int, str]]:
    default = settings.QR_TOKEN_TTL_MINUTES
    choices = {default: f"{default} daqiqa (standart)"}
    for minutes, label in [
        (60, "1 soat"),
        (24 * 60, "1 kun"),
        (3 * 24 * 60, "3 kun"),
        (7 * 24 * 60, "7 kun"),
    ]:
        choices.setdefault(minutes, label)
    return sorted(choices.items())


class QrTicketForm(forms.Form):
    ttl_minutes = forms.TypedChoiceField(
        label="Amal qilish muddati",
        coerce=int,
        choices=qr_lifetime_choices,
        initial=24 * 60,
        widget=forms.RadioSelect,
        help_text="Chipta shu vaqtgacha ishlaydi. Bir marta skanerlangach yaroqsiz bo‘ladi.",
    )
    output = forms.ChoiceField(
        label="Natija",
        choices=[
            ("print", "Chop etish uchun sahifa (QR rasmlari bilan)"),
            ("csv", "CSV fayl (tokenlar matn ko‘rinishida)"),
        ],
        initial="print",
        widget=forms.RadioSelect,
    )


def qr_svg(content: str) -> str:
    # segno draws only a path; the content (a URL or URL-safe token) is not embedded in the SVG.
    return mark_safe(segno.make(content, error="m").svg_inline(omitsize=True, border=2))


class PupilInline(admin.TabularInline):
    """On a classroom's page, so a whole class list can be typed in one go."""

    model = Pupil
    form = PupilAdminForm
    fields = ["last_name", "first_name", "middle_name", "imie", "status"]
    extra = 1
    show_change_link = True


@admin.register(Pupil)
class PupilAdmin(admin.ModelAdmin):
    form = PupilAdminForm
    list_display = ["__str__", "classroom_name", "school_name", "status"]
    list_filter = [
        "status",
        graduated_filter("classroom__graduated_year"),
        *hierarchy_filters(
            "classroom__school__district__region",
            "classroom__school__district",
            "classroom__school",
            "classroom",
        ),
    ]
    list_select_related = ["classroom__school"]
    search_fields = ["last_name", "first_name", "middle_name"]
    autocomplete_fields = ["classroom"]
    actions = ["issue_qr_tickets"]

    @admin.display(description="Sinf", ordering="classroom__name")
    def classroom_name(self, pupil) -> str:
        return pupil.classroom.name

    @admin.display(description="Maktab", ordering="classroom__school__name")
    def school_name(self, pupil) -> str:
        return pupil.classroom.school.name

    def get_search_results(self, request, queryset, search_term):
        # IMIE isn't searchable as text because it is hashed, but an exact match still works.
        if re.fullmatch(r"\d{14}", search_term):
            return queryset.filter(imie_hash=hash_imie(search_term)), False
        return super().get_search_results(request, queryset, search_term)

    # Whoever holds a ticket can log in as that pupil, so viewing the list is not enough.
    def has_issue_qr_permission(self, request) -> bool:
        return request.user.has_perm("accounts.change_pupil")

    @admin.action(description="QR chiptalar yaratish", permissions=["issue_qr"])
    def issue_qr_tickets(self, request, queryset):
        pupils = queryset.active().order_by(
            "classroom__school__district__name",
            "classroom__school__number",
            "classroom__number",
            "classroom__category",
            "last_name",
            "first_name",
        )
        count = pupils.count()
        if count > MAX_QR_TICKETS:
            self.message_user(
                request,
                f"Bir martada ko‘pi bilan {MAX_QR_TICKETS} ta chipta yaratiladi, "
                f"{count} ta tanlandi. Ro‘yxatni maktab yoki sinf bo‘yicha filtrlang.",
                messages.ERROR,
            )
            return None
        if not count:
            self.message_user(
                request,
                "Tanlanganlar orasida tizimga kira oladigan o‘quvchi yo‘q "
                "(o‘chirilgan yoki bitirgan).",
                messages.WARNING,
            )
            return None

        form = QrTicketForm(request.POST if request.POST.get("issue") == "yes" else None)
        if not form.is_valid():
            context = {
                **self.admin_site.each_context(request),
                "opts": self.opts,
                "title": "QR chiptalar yaratish",
                "form": form,
                "count": count,
                "skipped": queryset.count() - count,
                "qr_login_url": settings.QR_LOGIN_URL,
                # Re-posted with the form, so the action runs on exactly the same pupils.
                "select_across": request.POST.get("select_across") == "1",
                "selected": request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
                "action": "issue_qr_tickets",
            }
            return TemplateResponse(request, "admin/accounts/pupil/qr_tickets_form.html", context)

        tickets = issue_qr_tokens(list(pupils), form.cleaned_data["ttl_minutes"])
        if form.cleaned_data["output"] == "csv":
            return self._qr_csv(tickets)
        context = {
            "title": "QR chiptalar",
            "tickets": [
                {"pupil": pupil, "svg": qr_svg(qr_payload(raw)), "expires_at": entry.expires_at}
                for pupil, raw, entry in tickets
            ],
            "back_url": request.get_full_path(),
            "link_mode": bool(settings.QR_LOGIN_URL),
        }
        response = TemplateResponse(request, "admin/accounts/pupil/qr_tickets_print.html", context)
        response["Cache-Control"] = "no-store"  # the page holds live login tokens
        return response

    @staticmethod
    def _qr_csv(tickets) -> HttpResponse:
        """Raw tokens exist only in this response; they can't be recovered later."""
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="qr_tokens.csv"'
        response["Cache-Control"] = "no-store"
        writer = csv.writer(response)
        writer.writerow(["pupil", "class", "school", "token", "link", "expires_at"])
        for pupil, raw, entry in tickets:
            writer.writerow(
                [
                    str(pupil),
                    pupil.classroom.name,
                    pupil.classroom.school.name,
                    raw,
                    qr_payload(raw),
                    entry.expires_at.isoformat(),
                ]
            )
        return response


@admin.register(QrLoginToken)
class QrLoginTokenAdmin(admin.ModelAdmin):
    list_display = ["pupil", "created_at", "expires_at", "used_at"]
    list_select_related = ["pupil"]
    readonly_fields = ["pupil", "expires_at", "used_at", "created_at"]

    def has_add_permission(self, request) -> bool:
        return False  # tokens come from the Pupil list action, which can show the raw value
