import json

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.options import IncorrectLookupParameters
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count
from django.forms.models import BaseInlineFormSet
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django_ckeditor_5.widgets import CKEditor5Widget
from import_export.forms import ConfirmImportForm

from apps.core.sheets import (
    MAX_FILE_BYTES,
    ExcelFormat,
    JsonFormat,
    SheetAdminMixin,
    SheetImportForm,
)
from apps.schools.filters import hierarchy_filters
from apps.schools.models import Classroom, District, Region, School

from . import report_files
from .importer import export_exam_data, import_exams_data
from .models import (
    AnswerOption,
    Difficulty,
    Exam,
    ExamAttempt,
    ExamResult,
    ExamSection,
    ExamTarget,
    Question,
    Subject,
)
from .reports import PLACE_LEVELS, build_report
from .resources import QuestionResource
from .selectors import attempt_questions

NO_TARGETS = "Hech kimga (biriktirilmagan)"
PLACE_PARAMS = [param for param, _, _ in PLACE_LEVELS]


class ExamSectionInline(admin.TabularInline):
    model = ExamSection
    extra = 0


class ExamTargetInline(admin.TabularInline):
    model = ExamTarget
    fields = ["region", "district", "school", "classroom", "grade"]
    autocomplete_fields = ["region", "district", "school", "classroom"]
    extra = 1


class ExamJsonImportForm(forms.Form):
    file = forms.FileField(
        label="JSON fayl", widget=forms.ClearableFileInput(attrs={"accept": ".json"})
    )
    publish = forms.BooleanField(label="Darhol e’lon qilish", required=False)

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > MAX_FILE_BYTES:
            raise ValidationError(f"Fayl {MAX_FILE_BYTES // (1024 * 1024)} MB dan katta.")
        try:
            return json.loads(upload.read().decode("utf-8-sig"))
        except (UnicodeDecodeError, ValueError) as error:
            raise ValidationError(
                "Fayl JSON emas yoki buzilgan. U UTF-8 kodlashda va { bilan boshlansin."
            ) from error


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ["title", "audience", "duration_minutes", "is_published", "available_from"]
    list_filter = ["is_published"]
    search_fields = ["title"]
    inlines = [ExamTargetInline, ExamSectionInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "targets__region",
                "targets__district",
                "targets__school__district",
                "targets__classroom__school__district",
            )
        )

    # ------------------------------------------------------------ the whole exam as JSON

    def get_urls(self):
        own = [
            path(
                "import-json/",
                self.admin_site.admin_view(self.import_json_view),
                name="exams_exam_import_json",
            ),
            path(
                "<path:object_id>/export-json/",
                self.admin_site.admin_view(self.export_json_view),
                name="exams_exam_export_json",
            ),
        ]
        return own + super().get_urls()  # own first: the default "<object_id>/" would catch them

    def has_json_import_permission(self, request) -> bool:
        models = ["exam", "examsection", "examtarget", "question", "answeroption"]
        return request.user.has_perms([f"exams.add_{model}" for model in models])

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "has_json_import_permission": self.has_json_import_permission(request),
        }
        return super().changelist_view(request, extra_context)

    def import_json_view(self, request):
        if not self.has_json_import_permission(request):
            raise PermissionDenied
        form = ExamJsonImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                outcomes = import_exams_data(
                    form.cleaned_data["file"], publish=form.cleaned_data["publish"]
                )
                created = [outcome.exam for outcome in outcomes]
            except ValueError as error:
                form.add_error("file", f"Hech narsa saqlanmadi. {error}")
            else:
                if len(created) == 1:
                    return self._imported(request, created[0])
                for exam in created:
                    self.log_addition(request, exam, "JSON fayldan yuklandi.")
                self.message_user(
                    request,
                    f"{len(created)} ta imtihon yaratildi: "
                    + ", ".join(f"“{exam}”" for exam in created)
                    + ". Har birini tekshirib, “Kimga” bo‘limini ko‘rib chiqing.",
                    messages.SUCCESS,
                )
                return redirect("admin:exams_exam_changelist")
        context = {
            **self.admin_site.each_context(request),
            "opts": self.opts,
            "title": "Imtihonni JSON fayldan yuklash",
            "form": form,
            "max_file_mb": MAX_FILE_BYTES // (1024 * 1024),
        }
        return TemplateResponse(request, "admin/exams/exam/import_json.html", context)

    def _imported(self, request, exam):
        self.log_addition(request, exam, "JSON fayldan yuklandi.")
        state = "e’lon qilindi" if exam.is_published else "hali e’lon qilinmagan"
        self.message_user(
            request,
            f"“{exam}” yaratildi: {exam.questions.count()} ta savol, {state}. Tekshirib chiqing.",
            messages.SUCCESS,
        )
        if not exam.targets.exists():
            self.message_user(
                request,
                "Imtihon hech kimga biriktirilmagan, shuning uchun uni hech bir o‘quvchi "
                "ko‘rmaydi. “Kimga” bo‘limida kimlar ishlashini tanlang.",
                messages.WARNING,
            )
        return redirect("admin:exams_exam_change", exam.pk)

    def export_json_view(self, request, object_id):
        exam = self.get_object(request, object_id)
        if exam is None:
            raise Http404
        if not self.has_view_permission(request, exam):
            raise PermissionDenied
        response = JsonResponse(
            export_exam_data(exam), json_dumps_params={"ensure_ascii": False, "indent": 1}
        )
        name = slugify(exam.title) or "imtihon"
        response["Content-Disposition"] = f'attachment; filename="{name}.json"'
        return response

    @admin.display(description="Kimga")
    def audience(self, exam) -> str:
        return "; ".join(str(target) for target in exam.targets.all()) or NO_TARGETS

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        exam = form.instance
        if exam.is_published and not exam.targets.exists():
            self.message_user(
                request,
                f"“{exam}” e’lon qilingan, lekin hech kimga biriktirilmagan, shuning uchun uni "
                "hech bir o‘quvchi ko‘rmaydi. “Kimga” bo‘limida viloyat, tuman, maktab, sinf yoki "
                "sinf raqamini tanlang.",
                messages.WARNING,
            )


class AnswerOptionFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        kept = [f for f in self.forms if f.cleaned_data and not f.cleaned_data.get("DELETE")]
        if sum(1 for form in kept if form.cleaned_data.get("is_correct")) != 1:
            raise ValidationError("Aynan bitta javob to‘g‘ri deb belgilanishi kerak.")


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    formset = AnswerOptionFormSet
    extra = 0


def _exam_field(**kwargs):
    return forms.ModelChoiceField(
        queryset=Exam.objects.order_by("-created_at"), label="Imtihon", **kwargs
    )


class QuestionImportForm(SheetImportForm):
    exam = _exam_field(
        help_text="Fayldagi hamma savollar shu imtihonga yoziladi: raqami bor savol yangilanadi, "
        "yangi raqam qo‘shiladi."
    )
    field_order = ["exam", "import_file"]


class QuestionConfirmImportForm(ConfirmImportForm):
    exam = _exam_field(widget=forms.HiddenInput)


@admin.register(Question)
class QuestionAdmin(SheetAdminMixin, admin.ModelAdmin):
    resource_classes = [QuestionResource]
    # A question with a picture doesn't fit into an Excel cell; JSON carries it whole.
    formats = [ExcelFormat, JsonFormat]
    import_form_class = QuestionImportForm
    confirm_form_class = QuestionConfirmImportForm
    list_display = ["number", "exam", "subject", "difficulty", "type"]
    list_filter = ["exam", "subject", "difficulty"]
    list_select_related = ["exam"]
    readonly_fields = ["preview"]
    list_display_links = ("exam", "subject")
    inlines = [AnswerOptionInline]

    # ------------------------------------------------------------------- import/export

    def get_import_resource_kwargs(self, request, **kwargs):
        form = kwargs.pop("form", None)
        exam = getattr(form, "cleaned_data", {}).get("exam") if form is not None else None
        return {**super().get_import_resource_kwargs(request, **kwargs), "exam": exam}

    def get_import_form_initial(self, request):
        # "Fayldan yuklash" pressed on a list filtered by one exam: that exam is preselected.
        return {"exam": request.GET.get("exam")}

    def get_confirm_form_initial(self, request, import_form):
        initial = super().get_confirm_form_initial(request, import_form)
        if import_form is not None:
            initial["exam"] = import_form.cleaned_data["exam"].pk
        return initial

    def changelist_view(self, request, extra_context=None):
        exam = request.GET.get("exam__id__exact")
        extra_context = {**(extra_context or {}), "import_query": f"?exam={exam}" if exam else ""}
        return super().changelist_view(request, extra_context)

    def get_export_queryset(self, request):
        return super().get_export_queryset(request).prefetch_related("options")

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # The question text gets the full toolbar; passages, explanations and the answer options
        # keep the short one (settings.CKEDITOR_5_CONFIGS).
        if db_field.name == "prompt":
            kwargs["widget"] = CKEditor5Widget(config_name="extended")
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    class Media:
        css = {"all": ["exams/katex/katex.min.css"]}
        js = [
            "exams/katex/katex.min.js",
            "exams/katex/auto-render.min.js",
            "exams/question_preview.js",
        ]

    @admin.display(description="O‘quvchi ko‘radigan ko‘rinish")
    def preview(self, question) -> str:
        if question.pk is None:
            return "Saqlangandan keyin shu yerda ko‘rinadi."
        # mark_safe is fine here: RichTextField cleaned this HTML before it was saved.
        options = format_html_join(
            "",
            '<li class="{}"><b>{}</b><div>{}</div>{}</li>',
            (
                (
                    "is-correct" if option.is_correct else "",
                    option.label,
                    mark_safe(option.content),
                    mark_safe('<span class="question-preview__tick">✓ to‘g‘ri</span>')
                    if option.is_correct
                    else "",
                )
                for option in question.options.all()
            ),
        )
        passage = (
            format_html(
                '<div class="question-preview__passage">{}</div>', mark_safe(question.passage)
            )
            if question.passage
            else ""
        )
        explanation = (
            format_html(
                '<div class="question-preview__explanation"><b>Izoh:</b> {}</div>',
                mark_safe(question.explanation),
            )
            if question.explanation
            else ""
        )
        return format_html(
            '<div class="question-preview">{}<div class="question-preview__prompt">{}</div>'
            '<ul class="question-preview__options">{}</ul>{}</div>',
            passage,
            mark_safe(question.prompt),
            options,
            explanation,
        )


class ReadOnlyAdmin(admin.ModelAdmin):
    """Records produced by the exam itself: staff can look, but can't rewrite a child's history."""

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(ExamAttempt)
class ExamAttemptAdmin(ReadOnlyAdmin):
    list_display = ["pupil", "exam", "status", "started_at", "expires_at"]
    list_filter = [
        "status",
        "exam",
        *hierarchy_filters(
            "pupil__classroom__school__district__region",
            "pupil__classroom__school__district",
            "pupil__classroom__school",
            "pupil__classroom",
        ),
    ]
    list_select_related = ["pupil", "exam"]
    search_fields = ["pupil__first_name", "pupil__last_name"]
    readonly_fields = ["answer_key"]
    actions = ["allow_retake"]

    @admin.display(description="Javob kaliti")
    def answer_key(self, attempt) -> str:
        """
        This pupil's own key: with shuffling, their question 1 and its letters differ from anyone
        else's. Handy for checking a disputed result against what the pupil actually saw.
        """
        questions = attempt_questions(attempt)
        if not questions:
            return "Savollar yo‘q."
        chosen = {a.question_id: a.selected_option_ids for a in attempt.answers.all()}
        subjects = dict(Subject.choices)
        rows = []
        for question in questions:
            correct = next((o.label for o in question.options if o.is_correct), "—")
            picked_ids = chosen.get(question.id, [])
            picked = ", ".join(o.label for o in question.options if str(o.id) in picked_ids)
            if not picked:
                verdict = "—"
            else:
                verdict = "✓" if picked == correct else "✗"
            rows.append(
                (
                    question.number,
                    subjects.get(question.subject, question.subject),
                    Difficulty(question.difficulty).label if question.difficulty else "—",
                    question.original_number,
                    correct,
                    picked or "—",
                    verdict,
                )
            )
        compact = format_html_join(
            ", ",
            '<span style="white-space:nowrap">{}-{}</span>',
            ((number, correct) for number, _, _, _, correct, _, _ in rows),
        )
        table = format_html_join(
            "",
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td><b>{}</b></td><td>{}</td>"
            "<td>{}</td></tr>",
            rows,
        )
        return format_html(
            '<p class="answer-key__compact">{}</p>'
            '<table class="answer-key"><thead><tr><th>№</th><th>Fan</th><th>Daraja</th>'
            "<th>Bazadagi savol №</th><th>To‘g‘ri javob</th><th>O‘quvchi javobi</th><th></th>"
            "</tr></thead><tbody>{}</tbody></table>",
            compact,
            table,
        )

    @admin.action(
        description="Qayta topshirishga ruxsat berish (urinish va natija o‘chiriladi)",
        permissions=["retake"],
    )
    def allow_retake(self, request, queryset):
        """
        The only way to delete an attempt. A named action instead of a generic delete, so that
        nobody removes a child's result by accident, or a result without its attempt.
        """
        count = queryset.count()
        self.log_deletions(request, queryset)
        queryset.delete()
        self.message_user(request, f"Qayta topshirishga ruxsat berildi: {count} ta o‘quvchi.")

    def has_retake_permission(self, request) -> bool:
        return request.user.has_perm("exams.delete_examattempt")


@admin.register(ExamResult)
class ExamResultAdmin(ReadOnlyAdmin):
    list_display = ["attempt", "correct", "total", "percent", "finish_reason", "completed_at"]
    list_filter = [
        "attempt__exam",
        "finish_reason",
        *hierarchy_filters(
            "attempt__pupil__classroom__school__district__region",
            "attempt__pupil__classroom__school__district",
            "attempt__pupil__classroom__school",
            "attempt__pupil__classroom",
        ),
    ]
    list_select_related = ["attempt__pupil", "attempt__exam"]
    search_fields = ["attempt__pupil__first_name", "attempt__pupil__last_name"]

    # ------------------------------------------- the report and its files (apps.exams.reports)

    EXAM_PARAM = "attempt__exam__id__exact"

    def get_urls(self):
        own = [
            path(
                "report/",
                self.admin_site.admin_view(self.report_view),
                name="exams_examresult_report",
            ),
            path(
                "report/download/<str:file_format>/",
                self.admin_site.admin_view(self.report_download_view),
                name="exams_examresult_report_download",
            ),
        ]
        return own + super().get_urls()  # own first: the default "<object_id>/" would catch them

    def _report_input(self, request):
        """The result list's own filters and search, so the report shows what the list shows."""
        if not self.has_view_permission(request):
            raise PermissionDenied
        try:
            changelist = self.get_changelist_instance(request)
        except IncorrectLookupParameters:
            raise Http404("Filtr noto‘g‘ri.") from None
        return changelist, changelist.queryset

    def _report_filters(self, request, exam) -> tuple[dict, list[dict]]:
        chosen = {}
        described = [{"label": "Imtihon", "value": exam.title}]
        models = {"region": Region, "district": District, "school": School, "classroom": Classroom}
        for param, label, _ in PLACE_LEVELS:
            value = request.GET.get(param, "")
            if value.isdigit():
                place = models[param].objects.filter(pk=value).first()
                if place is not None:
                    chosen[param] = value
                    described.append({"label": label, "value": getattr(place, "name", str(place))})
        reason = request.GET.get("finish_reason__exact")
        if reason in dict(ExamResult.FinishReason.choices):
            described.append(
                {"label": "Yakunlash", "value": str(ExamResult.FinishReason(reason).label)}
            )
        if request.GET.get("q"):
            described.append({"label": "Qidiruv", "value": request.GET["q"]})
        return chosen, described

    def _report(self, request):
        """(changelist, exam or None, report or None, exams to choose from)."""
        changelist, results = self._report_input(request)
        exam_id = request.GET.get(self.EXAM_PARAM)
        if not exam_id:
            exams = list(
                results.order_by()
                .values("attempt__exam_id", "attempt__exam__title")
                .annotate(count=Count("id"))
                .order_by("attempt__exam__title")
            )
            if len(exams) != 1:
                return changelist, None, None, exams
            exam_id = exams[0]["attempt__exam_id"]
            results = results.filter(attempt__exam_id=exam_id)
        exam = Exam.objects.filter(pk=exam_id).first()
        if exam is None:
            raise Http404
        chosen, described = self._report_filters(request, exam)
        report = build_report(exam, results, chosen=chosen, filters=described)
        return changelist, exam, report, []

    def report_view(self, request):
        changelist, exam, report, exams = self._report(request)
        query = changelist.get_query_string()
        if exam is not None and self.EXAM_PARAM not in request.GET:
            query = changelist.get_query_string({self.EXAM_PARAM: exam.pk})
        groups = (report or {}).get("groups")
        context = {
            **self.admin_site.each_context(request),
            "opts": self.opts,
            "title": f"Natijalar hisoboti: {exam}" if exam else "Natijalar hisoboti",
            "exam": exam,
            "report": report,
            "exam_choices": [
                {
                    "title": item["attempt__exam__title"],
                    "count": item["count"],
                    "url": changelist.get_query_string({self.EXAM_PARAM: item["attempt__exam_id"]}),
                }
                for item in exams
            ],
            "list_url": reverse("admin:exams_examresult_changelist") + query,
            "downloads": [
                {
                    "format": file_format,
                    "label": label,
                    "hint": hint,
                    "url": reverse("admin:exams_examresult_report_download", args=[file_format])
                    + query,
                }
                for file_format, label, hint in [
                    ("xlsx", "Excel", "Hamma jadvallar, filtr va saralash bilan"),
                    ("pdf", "PDF", "Chop etish va yuborish uchun"),
                    ("png", "Rasm (PNG)", "Telegram va taqdimot uchun qisqa ko‘rinish"),
                    ("json", "JSON", "Boshqa dasturlar uchun to‘liq ma’lumot"),
                ]
            ],
            # A row of the place table opens the report one level deeper.
            "drill_urls": {
                str(row["id"]): changelist.get_query_string(
                    {groups["param"]: row["id"], **({self.EXAM_PARAM: exam.pk} if exam else {})},
                    remove=[
                        p for p, _, _ in PLACE_LEVELS[PLACE_PARAMS.index(groups["param"]) + 1 :]
                    ],
                )
                for row in groups["rows"]
            }
            if groups
            else {},
        }
        return TemplateResponse(request, "admin/exams/examresult/report.html", context)

    def report_download_view(self, request, file_format):
        if file_format not in report_files.FORMATS:
            raise Http404
        _, exam, report, _ = self._report(request)
        if report is None:
            raise Http404("Avval bitta imtihonni tanlang.")
        content_type, _ = report_files.FORMATS[file_format]
        response = HttpResponse(report_files.render(report, file_format), content_type=content_type)
        name = report_files.file_name(report, file_format)
        response["Content-Disposition"] = f'attachment; filename="{name}"'
        return response
