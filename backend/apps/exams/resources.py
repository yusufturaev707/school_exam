"""
Columns of the question file in the admin's import/export (apps.core.sheets).

One row is one question with its answer options: columns "A" to "F" hold the options and
"To‘g‘ri javob" the letter of the right one. A file is imported into one exam, chosen on the
import page. A question is found by its number in that exam and updated; a new number adds a
question. Questions that are not in the file are left alone.

Texts may be the editor's HTML (that is what an export gives, so a file can go out and come back)
or plain text typed into Excel, which becomes paragraphs. Formulas go between $ signs as in the
editor. A question with a picture is too long for an Excel cell, so for those use JSON.
"""

from django.core.exceptions import ValidationError
from import_export.fields import Field

from apps.core.richtext import is_blank_html, sanitize_html
from apps.core.sheets import (
    ChoiceWidget,
    NumberWidget,
    RichTextWidget,
    SheetMeta,
    SheetResource,
    cell_text,
    to_html,
)

from .models import AnswerOption, Difficulty, Question, Subject

EXAM, NUMBER, SUBJECT, DIFFICULTY = "Imtihon", "Raqami", "Fan", "Qiyinlik"
PROMPT, PASSAGE, EXPLANATION, CORRECT = "Savol matni", "O‘qish uchun matn", "Izoh", "To‘g‘ri javob"
OPTION_LABELS = "ABCDEF"
# Letters typed on a Cyrillic keyboard look the same and mean the same here.
_LATIN = str.maketrans("АВСДЕФ", "ABCDEF")

SUBJECT_ALIASES = {
    "mantiq": Subject.IQ,
    "iq": Subject.IQ,
    "mantiqiy fikrlash": Subject.IQ,
    "ingliz": Subject.LANGUAGE,
    "english": Subject.LANGUAGE,
    "inglizcha": Subject.LANGUAGE,
}


def _option_column(label: str):
    def content(question) -> str:
        return next((o.content for o in question.options.all() if o.label == label), "")

    return content


def _correct_label(question) -> str:
    return next((o.label for o in question.options.all() if o.is_correct), "")


class SubjectWidget(ChoiceWidget):
    """A subject by its code, its name, or the title of its section in the exam."""

    def __init__(self, exam=None):
        aliases = dict(SUBJECT_ALIASES)
        if exam is not None:
            aliases.update({section.title: section.subject for section in exam.sections.all()})
        super().__init__(Subject.choices, aliases)


class QuestionResource(SheetResource):
    exam_title = Field(attribute="exam__title", column_name=EXAM, readonly=True)
    number = Field(attribute="number", column_name=NUMBER, widget=NumberWidget())
    subject = Field(attribute="subject", column_name=SUBJECT, widget=SubjectWidget())
    difficulty = Field(
        attribute="difficulty", column_name=DIFFICULTY, widget=ChoiceWidget(Difficulty.choices)
    )
    prompt = Field(attribute="prompt", column_name=PROMPT, widget=RichTextWidget())
    passage = Field(attribute="passage", column_name=PASSAGE, widget=RichTextWidget())
    explanation = Field(attribute="explanation", column_name=EXPLANATION, widget=RichTextWidget())
    option_a = Field(column_name="A", dehydrate_method=_option_column("A"))
    option_b = Field(column_name="B", dehydrate_method=_option_column("B"))
    option_c = Field(column_name="C", dehydrate_method=_option_column("C"))
    option_d = Field(column_name="D", dehydrate_method=_option_column("D"))
    option_e = Field(column_name="E", dehydrate_method=_option_column("E"))
    option_f = Field(column_name="F", dehydrate_method=_option_column("F"))
    correct = Field(column_name=CORRECT, dehydrate_method=_correct_label)

    required_columns = (NUMBER,)
    column_help = {
        NUMBER: "Savolning imtihondagi raqami. Shu raqamli savol bo‘lsa, u yangilanadi.",
        SUBJECT: "Matematika, Mantiq (IQ) yoki Ingliz tili, yoki imtihondagi bo‘lim nomi.",
        DIFFICULTY: "Oson, O‘rta yoki Qiyin (1, 2, 3). Bo‘sh bo‘lishi mumkin.",
        PROMPT: "Oddiy matn yoki muharrir HTML'i. Formula $ belgilari orasida: $\\frac{1}{2}$.",
        PASSAGE: "Savolga oid uzun matn. Ixtiyoriy.",
        EXPLANATION: "Natija sahifasida ko‘rsatiladi. Ixtiyoriy.",
        "A": "Javob variantlari A dan boshlab ketma-ket, kamida ikkitasi (A–F).",
        CORRECT: "To‘g‘ri variant harfi, masalan B.",
    }
    sample_rows = [
        {
            NUMBER: 1,
            SUBJECT: "Matematika",
            DIFFICULTY: "Oson",
            PROMPT: "Hisoblang: 4 508 + 2 397",
            "A": "6 805",
            "B": "6 905",
            "C": "6 895",
            "D": "7 005",
            CORRECT: "B",
        },
        {
            NUMBER: 2,
            SUBJECT: "Matematika",
            DIFFICULTY: "O‘rta",
            PROMPT: "Kasrni qisqartiring: $\\frac{6}{8}$",
            "A": "$\\frac{3}{4}$",
            "B": "$\\frac{2}{3}$",
            "C": "$\\frac{1}{2}$",
            CORRECT: "A",
            EXPLANATION: "Surat va maxrajni 2 ga bo‘lamiz.",
        },
    ]

    class Meta(SheetMeta):
        model = Question
        fields = (
            "exam_title",
            "number",
            "subject",
            "difficulty",
            "prompt",
            "passage",
            "explanation",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "option_e",
            "option_f",
            "correct",
        )
        import_id_fields = ("number",)

    def __init__(self, exam=None, **kwargs):
        super().__init__(**kwargs)
        self.exam = exam
        self.fields["subject"].widget = SubjectWidget(exam)
        self._has_attempts = exam is not None and exam.attempts.exists()
        self._section_subjects = (
            {section.subject for section in exam.sections.all()} if exam is not None else set()
        )

    # ------------------------------------------------------------------------- export

    def before_export(self, queryset, **kwargs):
        stray = (
            AnswerOption.objects.filter(question__in=queryset)
            .exclude(label__in=list(OPTION_LABELS))
            .select_related("question")
            .first()
        )
        if stray is not None:
            raise ValueError(
                f"“{stray.question.exam}” imtihonidagi {stray.question.number}-savolda "
                f"“{stray.label}” harfli variant bor. Faylda faqat A–F ustunlari bor, shuning "
                "uchun avval variant harfini admin'da tuzating."
            )

    # ------------------------------------------------------------------------- import

    def init_instance(self, row=None):
        return Question(exam=self.exam)

    def get_instance(self, instance_loader, row):
        number = self.cleaned("number", row)
        if self.exam is None or number is None:
            return None
        return Question.objects.filter(exam=self.exam, number=number).first()

    def row_key(self, instance):
        return instance.number

    def check_row(self, instance, row, errors: dict, **kwargs) -> None:
        super().check_row(instance, row, errors, **kwargs)
        if (
            self._section_subjects
            and instance.subject
            and SUBJECT not in errors
            and instance.subject not in self._section_subjects
        ):
            errors[SUBJECT] = [
                f"“{self.exam}” imtihonida “{Subject(instance.subject).label}” bo‘limi yo‘q. "
                "Avval imtihonga shu bo‘limni qo‘shing yoki fanni to‘g‘rilang."
            ]
        instance._sheet_options = self._read_options(instance, row, errors)

    def _read_options(self, instance, row, errors: dict):
        """{label: cleaned HTML}, correct label; None when the file has no option columns."""
        if not any(column in row for column in (*OPTION_LABELS, CORRECT)):
            return None  # e.g. a file with only the explanations: options stay as they are

        options = {}
        for label in OPTION_LABELS:
            problems: list[str] = []
            content = sanitize_html(to_html(row.get(label)), problems)
            if problems:
                errors[label] = problems
            elif not is_blank_html(content):
                options[label] = content

        labels = "".join(options)
        if len(labels) < 2:
            errors.setdefault("A", ["Kamida ikkita javob varianti bo‘lsin: A va B ustunlari."])
        elif labels != OPTION_LABELS[: len(labels)]:
            errors.setdefault(
                "A", ["Variantlar A dan boshlab ketma-ket bo‘lsin, orada bo‘sh ustun qolmasin."]
            )

        correct = cell_text(row.get(CORRECT)).upper().translate(_LATIN).rstrip(").")
        if not correct:
            errors[CORRECT] = ["To‘g‘ri javob harfini yozing, masalan B."]
        elif correct not in options:
            errors[CORRECT] = [f"“{correct}” varianti bo‘sh yoki yo‘q."]

        if self._has_attempts and not instance._state.adding:
            removed = sorted({option.label for option in instance.options.all()} - set(options))
            if removed:
                errors[CORRECT if CORRECT in errors else removed[0]] = [
                    "Bu imtihonni o‘quvchilar ishlagan, shuning uchun variantni o‘chirib "
                    f"bo‘lmaydi: {', '.join(removed)}. Matnini o‘zgartirish mumkin."
                ]
        return options, correct

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if instance._state.adding or not super().skip_row(
            instance, original, row, import_validation_errors
        ):
            return False
        pending = getattr(instance, "_sheet_options", None)
        return pending is None or pending == self._stored_options(instance)

    @staticmethod
    def _stored_options(question):
        options = list(question.options.all())
        correct = next((option.label for option in options if option.is_correct), "")
        return {option.label: option.content for option in options}, correct

    def after_save_instance(self, instance, row, **kwargs):
        pending = getattr(instance, "_sheet_options", None)
        if pending is None:
            return
        options, correct = pending
        existing = {option.label: option for option in instance.options.all()}
        for label, content in options.items():
            option = existing.pop(label, None) or AnswerOption(question=instance, label=label)
            option.content = content
            option.is_correct = label == correct
            try:
                option.full_clean()
            except ValidationError as error:
                raise ValidationError({label: error.messages}) from error
            option.save()
        for option in existing.values():
            option.delete()
