import secrets
from dataclasses import asdict

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone

from apps.accounts.admin import PupilInline
from apps.accounts.pupil_import import (
    MAX_FILE_BYTES,
    MAX_ROWS,
    TEMPLATE_HEADERS,
    ImportFileError,
    PupilRow,
    apply_import,
    build_template,
    plan_import,
    read_rows,
)
from apps.core.sheets import SheetAdminMixin

from .filters import graduated_filter, hierarchy_filters
from .models import FINAL_GRADE, Classroom, District, Region, School
from .resources import DistrictResource, RegionResource, SchoolResource
from .services import PromotionError, promote_school

# Checked rows wait here between the preview and "Tasdiqlash". They hold IMIE hashes, not IMIEs.
IMPORT_SESSION_KEY = "pupil_import"


def _ordered(queryset):
    """
    Django drops Meta.ordering once a query has GROUP BY (any Count), so autocomplete lists came
    back in random order. The changelist's own column sorting still applies on top of this.
    """
    return queryset.order_by(*queryset.model._meta.ordering)


class NarrowedByParentPlaces:
    """
    Autocomplete lists narrowed by the wider places chosen in the same form row: in an exam's
    "Kimga" row, the school list shows only the chosen district's schools. The admin script
    (core/admin/material.js) sends those choices as ?region=…&district=…&school=….
    """

    # Request parameter -> lookup on this model.
    autocomplete_parents: dict[str, str] = {}

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(request, queryset, search_term)
        match = request.resolver_match
        if match is None or match.url_name != "autocomplete":
            return queryset, may_have_duplicates
        for param, lookup in self.autocomplete_parents.items():
            value = request.GET.get(param)
            if not value:
                continue
            try:
                queryset = queryset.filter(**{lookup: value})
            except (ValueError, ValidationError):  # not an id: nothing can match it
                return queryset.none(), False
        return queryset, may_have_duplicates


class DistrictInline(admin.TabularInline):
    model = District
    extra = 0
    show_change_link = True


class SchoolInline(admin.TabularInline):
    model = School
    fields = ["number", "name", "status"]
    extra = 0
    show_change_link = True


class ClassroomInline(admin.TabularInline):
    model = Classroom
    fields = ["number", "category", "name", "count", "status"]
    extra = 0
    show_change_link = True

    def get_queryset(self, request):
        # Past graduates are in the classroom list (filter "Bitirganlar"), not on the school page.
        return super().get_queryset(request).current()


@admin.register(Region)
class RegionAdmin(SheetAdminMixin, admin.ModelAdmin):
    resource_classes = [RegionResource]
    list_display = ["number", "name", "district_count", "status"]
    list_display_links = ["name"]
    list_filter = ["status"]
    search_fields = ["name"]
    inlines = [DistrictInline]

    def get_queryset(self, request):
        return _ordered(super().get_queryset(request).annotate(_districts=Count("districts")))

    @admin.display(description="Tumanlar", ordering="_districts")
    def district_count(self, region) -> int:
        return region._districts


@admin.register(District)
class DistrictAdmin(SheetAdminMixin, NarrowedByParentPlaces, admin.ModelAdmin):
    resource_classes = [DistrictResource]
    autocomplete_parents = {"region": "region"}
    list_display = ["number", "name", "region", "school_count", "status"]
    list_display_links = ["name"]
    list_filter = ["status", "region"]
    list_select_related = ["region"]
    search_fields = ["name", "region__name"]
    autocomplete_fields = ["region"]
    inlines = [SchoolInline]

    def get_queryset(self, request):
        return _ordered(super().get_queryset(request).annotate(_schools=Count("schools")))

    @admin.display(description="Maktablar", ordering="_schools")
    def school_count(self, district) -> int:
        return district._schools


class PupilImportForm(forms.Form):
    file = forms.FileField(
        label="Fayl (.xlsx yoki .csv)",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx,.csv"}),
    )
    create_classrooms = forms.BooleanField(
        label="Faylda bor, lekin maktabda yo‘q sinflarni yaratish",
        required=False,
        initial=True,
    )


@admin.register(School)
class SchoolAdmin(SheetAdminMixin, NarrowedByParentPlaces, admin.ModelAdmin):
    resource_classes = [SchoolResource]
    autocomplete_parents = {"region": "district__region", "district": "district"}
    list_display = [
        "number",
        "name",
        "district",
        "classroom_count",
        "last_promoted_year",
        "status",
    ]
    list_display_links = ["name"]
    list_filter = ["status", *hierarchy_filters("district__region", "district")]
    search_fields = ["name", "number", "district__name"]
    autocomplete_fields = ["district"]
    inlines = [ClassroomInline]
    actions = ["promote_to_next_year"]
    # Adds the "O'quvchilarni yuklash" button next to "Tarix".
    change_form_template = "admin/schools/school/change_form.html"

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("district")
        return _ordered(
            queryset.annotate(
                _classrooms=Count("classrooms", filter=Q(classrooms__graduated_year__isnull=True))
            )
        )

    @admin.display(description="Sinflar", ordering="_classrooms")
    def classroom_count(self, school) -> int:
        return school._classrooms

    def get_urls(self):
        own = [
            path(
                "<path:object_id>/import-pupils/",
                self.admin_site.admin_view(self.import_pupils_view),
                name="schools_school_import_pupils",
            ),
            path(
                "import-pupils/template.xlsx",
                self.admin_site.admin_view(self.import_template_view),
                name="schools_school_import_template",
            ),
        ]
        return own + super().get_urls()  # own first: the default "<object_id>/" would catch them

    # ------------------------------------------------------------------------- pupil import

    def has_import_permission(self, request) -> bool:
        return request.user.has_perms(["accounts.add_pupil", "accounts.change_pupil"])

    def import_template_view(self, request):
        if not self.has_import_permission(request):
            raise PermissionDenied
        response = HttpResponse(
            build_template(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="oquvchilar_namuna.xlsx"'
        return response

    def import_pupils_view(self, request, object_id):
        school = self.get_object(request, object_id)
        if school is None:
            raise Http404
        if not (self.has_view_permission(request, school) and self.has_import_permission(request)):
            raise PermissionDenied

        context = {
            **self.admin_site.each_context(request),
            "opts": self.opts,
            "school": school,
            "title": f"O‘quvchilarni yuklash: {school}",
            "columns": TEMPLATE_HEADERS,
            "max_rows": MAX_ROWS,
            "max_file_mb": MAX_FILE_BYTES // (1024 * 1024),
        }
        if request.method == "POST" and "confirm" in request.POST:
            return self._confirm_import(request, school, context)

        form = PupilImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            create = form.cleaned_data["create_classrooms"]
            if create and not request.user.has_perm("schools.add_classroom"):
                form.add_error("create_classrooms", "Sizda sinf qo‘shish huquqi yo‘q.")
            else:
                try:
                    rows, errors = read_rows(form.cleaned_data["file"])
                except ImportFileError as error:
                    form.add_error("file", str(error))
                else:
                    return self._preview(request, school, context, rows, errors, create)
        context["form"] = form
        return TemplateResponse(request, "admin/schools/school/import_pupils.html", context)

    def _preview(self, request, school, context, rows, errors, create):
        plan = plan_import(school, rows, create, errors)
        if plan.ok and plan.has_changes:
            token = secrets.token_urlsafe(16)
            request.session[IMPORT_SESSION_KEY] = {
                "token": token,
                "school": school.pk,
                "create": create,
                "rows": [asdict(row) for row in rows],
            }
            context["token"] = token
        context["plan"] = plan
        return TemplateResponse(request, "admin/schools/school/import_preview.html", context)

    def _confirm_import(self, request, school, context):
        import_url = reverse("admin:schools_school_import_pupils", args=[school.pk])
        pending = request.session.get(IMPORT_SESSION_KEY)
        if (
            not pending
            or pending["school"] != school.pk
            or not secrets.compare_digest(pending["token"], request.POST.get("token", ""))
        ):
            self.message_user(request, "Bu yuklash eskirgan. Faylni qayta yuklang.", messages.ERROR)
            return redirect(import_url)

        rows = [PupilRow(**row) for row in pending["rows"]]
        try:
            plan = apply_import(school.pk, rows, pending["create"])
        except IntegrityError:
            # Someone saved the same pupil or class between our check and our insert.
            self.message_user(
                request,
                "Shu paytda ro‘yxat boshqa joyda o‘zgardi. Faylni qayta yuklang.",
                messages.ERROR,
            )
            return redirect(import_url)
        del request.session[IMPORT_SESSION_KEY]

        if not plan.ok:  # the database changed after the preview
            context["plan"] = plan
            return TemplateResponse(request, "admin/schools/school/import_preview.html", context)

        summary = (
            f"yangi o‘quvchilar: {len(plan.created)}, yangilandi: {len(plan.updated)}, "
            f"boshqa maktabdan o‘tkazildi: {len(plan.moved)}, o‘zgarmadi: {plan.unchanged}, "
            f"yangi sinflar: {len(plan.new_classrooms)}"
        )
        self.log_change(request, school, f"O‘quvchilar ro‘yxati fayldan yuklandi: {summary}.")
        self.message_user(request, f"Saqlandi. {summary.capitalize()}.", messages.SUCCESS)
        return redirect("admin:schools_school_change", school.pk)

    # ---------------------------------------------------------------------- yearly promotion

    def has_promote_permission(self, request) -> bool:
        return request.user.has_perms(["schools.change_school", "schools.change_classroom"])

    @admin.action(description="Keyingi o‘quv yiliga o‘tkazish", permissions=["promote"])
    def promote_to_next_year(self, request, queryset):
        year = timezone.localdate().year
        if request.POST.get("confirm") != "yes":
            return self._promotion_confirmation(request, queryset, year)

        promoted = skipped = 0
        for school in queryset:
            try:
                result = promote_school(school.pk, year)
            except PromotionError as error:
                skipped += 1
                self.message_user(request, str(error), messages.WARNING)
                continue
            promoted += 1
            self.log_change(
                request,
                school,
                f"{year}: {result.promoted} ta sinf keyingi sinfga o‘tdi, "
                f"{result.graduated} ta sinf bitirdi.",
            )
        if promoted:
            self.message_user(
                request, f"Keyingi o‘quv yiliga o‘tkazildi: {promoted} ta maktab.", messages.SUCCESS
            )
        return None

    def _promotion_confirmation(self, request, queryset, year):
        # A fresh queryset: the changelist's own annotation would be counted wrongly next to these.
        current = Q(classrooms__graduated_year__isnull=True)
        final = current & Q(classrooms__number__gte=FINAL_GRADE)
        schools = (
            School.objects.filter(pk__in=queryset.values("pk"))
            .select_related("district")
            .annotate(
                moving=Count("classrooms", filter=current & ~final, distinct=True),
                leaving=Count("classrooms", filter=final, distinct=True),
                leaving_pupils=Count("classrooms__pupils", filter=final, distinct=True),
            )
        )
        rows = list(schools)
        # Totals cover only the schools that will move: the ones done this year are skipped.
        ready = [school for school in rows if school.last_promoted_year != year]
        context = {
            **self.admin_site.each_context(request),
            "opts": self.opts,
            "title": "Keyingi o‘quv yiliga o‘tkazish",
            "year": year,
            "final_grade": FINAL_GRADE,
            "ready": ready,
            "done_already": [school for school in rows if school.last_promoted_year == year],
            "totals": {
                key: sum(getattr(school, key) for school in ready)
                for key in ("moving", "leaving", "leaving_pupils")
            },
            # Re-posted on "Ha, o'tkazish", so the action runs on exactly the same schools.
            "select_across": request.POST.get("select_across") == "1",
            "selected": request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
            "action": "promote_to_next_year",
        }
        return TemplateResponse(request, "admin/schools/school/promote_confirmation.html", context)


@admin.register(Classroom)
class ClassroomAdmin(NarrowedByParentPlaces, admin.ModelAdmin):
    autocomplete_parents = {
        "region": "school__district__region",
        "district": "school__district",
        "school": "school",
    }
    list_display = ["name", "school", "number", "category", "count", "pupil_count", "status"]
    list_filter = [
        graduated_filter("graduated_year"),
        "status",
        "number",
        *hierarchy_filters("school__district__region", "school__district", "school"),
    ]
    search_fields = ["name", "school__name", "school__district__name"]
    autocomplete_fields = ["school"]
    # Set only by the yearly promotion: typing a year here by hand would hide a working class.
    readonly_fields = ["graduated_year"]
    inlines = [PupilInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("school__district")
        return _ordered(queryset.annotate(_pupils=Count("pupils")))

    @admin.display(description="Ro‘yxatda", ordering="_pupils")
    def pupil_count(self, classroom) -> int:
        return classroom._pupils
