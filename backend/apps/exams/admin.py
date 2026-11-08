from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from apps.schools.filters import hierarchy_filters

from .models import (
    AnswerOption,
    Exam,
    ExamAttempt,
    ExamResult,
    ExamSection,
    ExamTarget,
    Question,
)

NO_TARGETS = "Hech kimga (biriktirilmagan)"


class ExamSectionInline(admin.TabularInline):
    model = ExamSection
    extra = 0


class ExamTargetInline(admin.TabularInline):
    model = ExamTarget
    fields = ["region", "district", "school", "classroom", "grade"]
    autocomplete_fields = ["region", "district", "school", "classroom"]
    extra = 1


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


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["number", "exam", "subject", "type"]
    list_filter = ["exam", "subject"]
    list_select_related = ["exam"]
    readonly_fields = ["preview"]
    inlines = [AnswerOptionInline]

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
            "<li><b>{}</b>{} {}</li>",
            (
                (option.label, " ✓" if option.is_correct else "", mark_safe(option.content))
                for option in question.options.all()
            ),
        )
        return format_html(
            '<div class="question-preview">{}{}<ul>{}</ul>{}</div>',
            mark_safe(question.passage),
            mark_safe(question.prompt),
            options,
            mark_safe(question.explanation),
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
    actions = ["allow_retake"]

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
