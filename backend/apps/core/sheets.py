"""
File import and export in the admin, built on django-import-export and shared by the places
(apps.schools.resources) and the questions (apps.exams.resources).

What this module adds on top of the library:

- All or nothing. A file with one bad row saves nothing. The check page names the row and the
  column of every problem, and nothing is written before "Tasdiqlash".
- Lookups that forgive the way people type in Excel. "Farg'ona", "Farg‘ona" and "Fargʻona" are
  one name, "nomi " is the column "Nomi", and a region can be given by its name or its number.
- Excel files that are safe to open. Text such as "=2+3" stays text instead of becoming a formula.
  A value longer than an Excel cell holds (32 767 characters, e.g. a question with a picture)
  stops the export with a clear message instead of being cut off without a word: such data
  goes out as JSON.
"""

from __future__ import annotations

import html
import re
import unicodedata
import zipfile
from io import BytesIO

import tablib
from django import forms
from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_permission_codename
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    FieldDoesNotExist,
    PermissionDenied,
    ValidationError,
)
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import path
from django.utils import timezone
from django.utils.text import capfirst, slugify
from import_export import resources, widgets
from import_export.admin import ImportExportMixin
from import_export.formats import base_formats
from import_export.forms import ImportForm, SelectableFieldsExportForm
from import_export.resources import Diff
from import_export.results import Result, RowResult

from .richtext import ALLOWED_TAGS

EXCEL_CELL_LIMIT = 32_767
MAX_FILE_BYTES = 15 * 1024 * 1024  # nginx lets 16 MB through to /admin
MAX_ROWS = 5000
# An .xlsx is a zip, and a small one can unpack into gigabytes: checked before openpyxl opens it.
MAX_UNPACKED_BYTES = 80 * 1024 * 1024

# --------------------------------------------------------------------------- text from cells

_APOSTROPHES = str.maketrans(dict.fromkeys("‘’ʻʼ`´", "'"))


def name_key(value) -> str:
    """The form of a name used for comparing: case, spaces and apostrophe variants don't count."""
    text = unicodedata.normalize("NFKC", cell_text(value)).translate(_APOSTROPHES)
    return " ".join(text.split()).casefold()


def cell_text(value) -> str:
    """A cell as text. Excel hands over 5 as 5.0, which is still the number 5."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


_IMAGE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_BLOCK_END = re.compile(r"</(?:p|li|h\d|tr|td|th|figure|div|blockquote)>|<br\s*/?>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


def summary(value, limit: int = 120) -> str:
    """A short plain-text view of a cell for the check page, where HTML and pictures don't fit."""
    text = cell_text(value)
    if "<" in text:
        text = _IMAGE.sub(" [rasm] ", text)
        text = _BLOCK_END.sub(" ", text)
        text = html.unescape(_TAG.sub("", text))
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


# Only tags the editor itself makes count as HTML. "$a<b$ va $c>d$" has "<b$ va $c>" in it, which
# a looser test would take for a <b> tag and then mangle.
_HTML_TAG = re.compile(
    r"</?(?:{})(?=[\s/>])[^<>]*>".format("|".join(sorted(ALLOWED_TAGS))), re.IGNORECASE
)


def to_html(value) -> str:
    """
    Editor HTML as it is; plain text from a hand-filled cell becomes paragraphs, one per line.
    Both are cleaned afterwards by RichTextField, like anything typed into the admin.
    """
    if value is None:
        return ""
    text = value if isinstance(value, str) else cell_text(value)
    if _HTML_TAG.search(text):
        return text.strip()
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "".join(f"<p>{html.escape(line, quote=False)}</p>" for line in lines if line)


# ------------------------------------------------------------------------------------ widgets


class TextWidget(widgets.CharWidget):
    """A name: surrounding and doubled spaces removed."""

    def clean(self, value, row=None, **kwargs):
        return " ".join(cell_text(value).split())


class NumberWidget(widgets.Widget):
    def clean(self, value, row=None, **kwargs):
        text = cell_text(value)
        if not text:
            return None
        if not text.isdigit():
            raise ValueError(f"“{text}”: butun son yozing, masalan 5.")
        return int(text)

    def render(self, value, obj=None, **kwargs):
        return "" if value is None else value


class StatusWidget(widgets.Widget):
    """The "faol" switch as "ha" / "yo‘q". An empty cell keeps the current value (new: "ha")."""

    TRUE = {"ha", "1", "true", "faol", "+", "yes"}
    FALSE = {"yo'q", "yoq", "0", "false", "nofaol", "faol emas", "-", "no"}

    def clean(self, value, row=None, **kwargs):
        if isinstance(value, bool):
            return value
        key = name_key(value)
        if not key:
            return None
        if key in self.TRUE:
            return True
        if key in self.FALSE:
            return False
        raise ValueError(f"“{cell_text(value)}”: “ha” yoki “yo‘q” deb yozing.")

    def render(self, value, obj=None, **kwargs):
        return "ha" if value else "yo‘q"


class ChoiceWidget(widgets.Widget):
    """A choice by its code or its name: "math" and "Matematika" are the same subject."""

    def __init__(self, choices, aliases: dict | None = None):
        super().__init__()
        self.labels = {value: str(label) for value, label in choices}
        self.lookup = {name_key(value): value for value in self.labels}
        self.lookup.update({name_key(label): value for value, label in self.labels.items()})
        self.lookup.update({name_key(alias): value for alias, value in (aliases or {}).items()})

    def clean(self, value, row=None, **kwargs):
        key = name_key(value)
        if not key:
            return None
        if key not in self.lookup:
            allowed = ", ".join(self.labels.values())
            raise ValueError(f"“{cell_text(value)}” degan qiymat yo‘q. Mumkin: {allowed}.")
        return self.lookup[key]

    def render(self, value, obj=None, **kwargs):
        return self.labels.get(value, "" if value is None else str(value))


class RichTextWidget(widgets.Widget):
    def clean(self, value, row=None, **kwargs):
        return to_html(value)

    def render(self, value, obj=None, **kwargs):
        return value or ""


def pick(candidates, value, what: str):
    """
    One place out of `candidates` by its number ("14") or its name ("Toshkent shahri").
    Raises ValueError with a message for the check page when there is no single match.
    """
    text = cell_text(value)
    if text.isdigit():
        found = [c for c in candidates if c.number == int(text)]
    else:
        key = name_key(text)
        found = [c for c in candidates if name_key(c.name) == key]
    if not found:
        raise ValueError(f"“{text}” degan {what} topilmadi.")
    if len(found) > 1:
        raise ValueError(f"“{text}” degan {what} bir nechta. Raqamini yozing.")
    return found[0]


def find_existing(candidates, number, name):
    """The row's record among `candidates`: by number first, then by name."""
    if number is not None:
        for candidate in candidates:
            if candidate.number == number:
                return candidate
    key = name_key(name)
    if key:
        for candidate in candidates:
            if name_key(candidate.name) == key:
                return candidate
    return None


# ------------------------------------------------------------------------------------ formats


class SheetError(ValueError):
    """A problem with the file as a whole, shown under the file field as it is."""


def _tidy(dataset: tablib.Dataset) -> tablib.Dataset:
    headers = [cell_text(header) for header in dataset.headers or []]
    if not any(headers):
        raise SheetError("Birinchi qatorda ustun nomlari bo‘lsin (namuna fayldagidek).")
    keys = [name_key(header) for header in headers if header]
    if len(keys) != len(set(keys)):
        raise SheetError("Ustun nomlari takrorlanmasin: har bir ustun bir marta bo‘lsin.")
    tidy = tablib.Dataset(headers=headers)
    for row in dataset:
        if any(cell_text(value) for value in row):  # Excel keeps formatted empty rows
            tidy.append(row)
    if not tidy:
        raise SheetError("Faylda ma’lumot yo‘q: ustun nomlaridan keyin kamida bitta qator bo‘lsin.")
    if len(tidy) > MAX_ROWS:
        raise SheetError(f"Bitta faylda ko‘pi bilan {MAX_ROWS} ta qator bo‘lsin.")
    return tidy


class TidyMixin:
    def create_dataset(self, in_stream):
        return _tidy(super().create_dataset(in_stream))


class CsvFormat(TidyMixin, base_formats.CSV):
    label = "CSV (.csv)"


class JsonFormat(TidyMixin, base_formats.JSON):
    label = "JSON (.json): rasmli savollar ham to‘liq"


class ExcelFormat(TidyMixin, base_formats.XLSX):
    label = "Excel (.xlsx)"

    def create_dataset(self, in_stream):
        try:
            with zipfile.ZipFile(BytesIO(in_stream)) as archive:
                unpacked = sum(info.file_size for info in archive.infolist())
        except zipfile.BadZipFile as error:
            raise SheetError("Fayl Excel (.xlsx) emas yoki buzilgan.") from error
        if unpacked > MAX_UNPACKED_BYTES:
            raise SheetError("Excel fayl ichidagi ma’lumot juda katta.")
        return super().create_dataset(in_stream)

    def export_data(self, dataset, **kwargs):
        from openpyxl import Workbook
        from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter

        book = Workbook()
        sheet = book.active
        sheet.title = "Ma'lumotlar"
        headers = [str(header) for header in dataset.headers or []]
        sheet.append(headers)
        widths = [len(header) for header in headers]
        for line, row in enumerate(dataset, start=2):
            for column, value in enumerate(row, start=1):
                if isinstance(value, str):
                    if len(value) > EXCEL_CELL_LIMIT:
                        size = f"{len(value):,}".replace(",", " ")
                        raise ValueError(
                            f"{line}-qatordagi “{headers[column - 1]}” Excel katagiga sig‘maydi: "
                            f"{size} belgi, Excel'da esa ko‘pi bilan 32 767. Odatda bu matn "
                            "ichidagi rasm. Bunday ma’lumotni JSON formatida yuklab oling."
                        )
                    value = ILLEGAL_CHARACTERS_RE.sub("", value)
                cell = sheet.cell(row=line, column=column, value=value)
                if isinstance(value, str) and value.startswith("="):
                    cell.data_type = "s"  # text that only looks like a formula
                widths[column - 1] = max(widths[column - 1], min(len(cell_text(value)), 60))

        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D3EFE5")
        sheet.freeze_panes = "A2"
        for column, width in enumerate(widths, start=1):
            sheet.column_dimensions[get_column_letter(column)].width = max(width + 2, 8)

        output = BytesIO()
        book.save(output)
        return output.getvalue()


def format_label(file_format) -> str:
    return getattr(file_format, "label", file_format.get_title())


# ---------------------------------------------------------------------------------- resources


class SummaryDiff(Diff):
    """The check page compares short summaries: a question's HTML and pictures would not fit."""

    def __init__(self, resource, instance, new):
        self.left = self._values(resource, instance)
        self.right = []
        self.new = new

    def compare_with(self, resource, instance):
        self.right = self._values(resource, instance)

    @staticmethod
    def _values(resource, instance):
        fields = resource.get_import_fields()
        if instance is None:
            return ["" for _ in fields]
        return [summary(resource.export_field(field, instance)) for field in fields]


class SummaryResult(Result):
    def append_invalid_row(self, number, row, validation_error):
        super().append_invalid_row(
            number, {column: summary(value) for column, value in row.items()}, validation_error
        )


class SheetMeta:
    skip_unchanged = True
    report_skipped = False  # still counted in the totals; the table lists only real changes
    clean_model_instances = True  # model validation, including RichTextField's HTML cleaning
    use_transactions = True


class SheetResource(resources.ModelResource):
    """
    Base for the admin's import resources. Subclasses describe their columns for the import page
    (`column_help`, `required_columns`, `sample_rows`) and say how a row finds its record
    (`get_instance`) and what makes two rows the same record (`row_key`).
    """

    column_help: dict[str, str] = {}
    required_columns: tuple[str, ...] = ()
    sample_rows: list[dict] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._seen_keys: dict = {}

    @classmethod
    def get_diff_class(cls):
        return SummaryDiff

    @classmethod
    def get_result_class(cls):
        return SummaryResult

    def import_columns(self) -> list[str]:
        return [field.column_name for field in self.get_import_fields() if not field.readonly]

    def import_data(self, dataset, **kwargs):
        # The confirmed import rolls back on any row error, not only on exceptions. The data could
        # have changed since the check, and half a file must never end up in the database.
        kwargs["rollback_on_validation_errors"] = True
        return super().import_data(dataset, **kwargs)

    def before_import(self, dataset, **kwargs):
        known = {name_key(field.column_name): field.column_name for field in self.fields.values()}
        dataset.headers = [known.get(name_key(header), header) for header in dataset.headers]
        missing = [column for column in self.required_columns if column not in dataset.headers]
        if missing:
            # Without a key column every row would only repeat the same complaint: skip them.
            del dataset[:]
            raise SheetError(
                "Faylda kerakli ustun yo‘q: "
                + ", ".join(f"“{column}”" for column in missing)
                + ". Ustun nomlari namuna fayldagidek bo‘lsin."
            )

    def import_instance(self, instance, row, **kwargs):
        errors: dict = {}
        try:
            super().import_instance(instance, row, **kwargs)
        except ValidationError as error:
            errors = error.update_error_dict(errors)
        self.check_row(instance, row, errors, **kwargs)
        if errors:
            raise ValidationError(errors)

    def check_row(self, instance, row, errors: dict, **kwargs) -> None:
        """Adds row-level problems to `errors`. By default: the same record twice in one file."""
        if errors:
            return
        key = self.row_key(instance)
        if key is None:
            return
        line = kwargs.get("row_number")
        first = self._seen_keys.setdefault(key, line)
        if first != line:
            errors[NON_FIELD_ERRORS] = [
                f"Bu yozuv faylda ikki marta bor: {first + 1}-qatorda ham. Bittasini qoldiring."
            ]

    def row_key(self, instance):
        return None

    def import_row(self, row, instance_loader, **kwargs):
        row_result = super().import_row(row, instance_loader, **kwargs)
        error = row_result.validation_error
        if error is not None and hasattr(error, "error_dict"):
            # Model validation names fields ("region"); the person fixing the file sees columns.
            row_result.validation_error = ValidationError(
                {self._column_of(key): value for key, value in error.error_dict.items()}
            )
        return row_result

    def _column_of(self, key: str) -> str:
        if key == NON_FIELD_ERRORS:
            return key
        for field in self.fields.values():
            if key in (field.attribute, field.column_name):
                return field.column_name
        try:
            return capfirst(self._meta.model._meta.get_field(key).verbose_name)
        except FieldDoesNotExist:
            return key

    def cleaned(self, name: str, row):
        """A column's value for finding the record, or None when it is missing or invalid."""
        field = self.fields[name]
        if field.column_name not in row:
            return None
        try:
            return field.clean(row)
        except ValueError:
            return None  # reported against the column when the row is imported


# -------------------------------------------------------------------------------------- forms


class SheetImportForm(ImportForm):
    """The file only: its type comes from the extension, so there is no format list to get wrong."""

    def __init__(self, formats, resources, **kwargs):
        super().__init__(formats, resources, **kwargs)
        self.file_formats = [file_format() for file_format in formats]
        extensions = [f".{file_format.get_extension()}" for file_format in self.file_formats]
        upload = self.fields["import_file"]
        upload.label = "Fayl"
        upload.widget.attrs = {"accept": ",".join(extensions)}
        self.fields["format"].required = False
        self.fields["format"].widget = forms.HiddenInput()
        self.extensions = ", ".join(extensions)

    def clean(self):
        data = super().clean()
        upload = data.get("import_file")
        if not upload:
            return data
        if upload.size > MAX_FILE_BYTES:
            self.add_error("import_file", f"Fayl {MAX_FILE_BYTES // (1024 * 1024)} MB dan katta.")
            return data
        extension = upload.name.rsplit(".", 1)[-1].lower() if "." in upload.name else ""
        for index, file_format in enumerate(self.file_formats):
            if file_format.get_extension() == extension:
                data["format"] = str(index)
                return data
        self.add_error("import_file", f"Bu fayl turi qabul qilinmaydi. Mumkin: {self.extensions}.")
        return data


class SheetExportForm(SelectableFieldsExportForm):
    def __init__(self, formats, resources, **kwargs):
        super().__init__(formats, resources, **kwargs)
        field = self.fields["format"]
        field.label = "Fayl turi"
        field.choices = [(str(i), format_label(f())) for i, f in enumerate(formats)]
        field.widget = forms.RadioSelect(choices=field.choices)
        field.initial = "0"

    def _get_field_label(self, resource, field_name):
        field = resource.fields.get(field_name)
        return field.column_name if field else field_name


# -------------------------------------------------------------------------------------- admin


class SheetAdminMixin(ImportExportMixin):
    """
    "Fayldan yuklash" and "Yuklab olish" buttons on a changelist. Export takes the list as it is
    filtered and searched. Import needs both the add and the change permission, since a file both
    adds and updates records; export needs only the view permission.
    """

    formats = [ExcelFormat, CsvFormat]
    import_template_name = "admin/sheets/import.html"
    export_template_name = "admin/sheets/export.html"
    import_export_change_list_template = "admin/sheets/change_list.html"
    import_form_class = SheetImportForm
    export_form_class = SheetExportForm

    def has_import_permission(self, request) -> bool:
        opts = self.opts
        return all(
            request.user.has_perm(f"{opts.app_label}.{get_permission_codename(action, opts)}")
            for action in ("add", "change")
        )

    def has_export_permission(self, request) -> bool:
        return self.has_view_permission(request)

    def get_urls(self):
        info = self.get_model_info()
        own = [
            path(
                "import/template/",
                self.admin_site.admin_view(self.import_sample_view),
                name="{}_{}_import_sample".format(*info),
            )
        ]
        return own + super().get_urls()

    # ------------------------------------------------------------------------------ import

    def import_resource(self, request):
        resource_class = self.get_import_resource_classes(request)[0]
        return resource_class(**self.get_import_resource_kwargs(request))

    def get_import_context_data(self, **kwargs):
        return {"sheet_import": True}

    def import_action(self, request, **kwargs):
        response = super().import_action(request, **kwargs)
        if hasattr(response, "context_data"):
            resource = self.import_resource(request)
            response.context_data.update(
                {
                    "title": f"{capfirst(self.opts.verbose_name_plural)}: fayldan yuklash",
                    "columns": [
                        {
                            "name": column,
                            "help": resource.column_help.get(column, ""),
                            "required": column in resource.required_columns,
                        }
                        for column in resource.import_columns()
                    ],
                    "max_file_mb": MAX_FILE_BYTES // (1024 * 1024),
                    "max_rows": MAX_ROWS,
                    "sample_url": "admin:{}_{}_import_sample".format(*self.get_model_info()),
                }
            )
        return response

    def import_sample_view(self, request):
        if not self.has_import_permission(request):
            raise PermissionDenied
        resource = self.import_resource(request)
        columns = resource.import_columns()
        dataset = tablib.Dataset(headers=columns)
        for sample in resource.sample_rows:
            dataset.append([sample.get(column, "") for column in columns])
        response = HttpResponse(
            ExcelFormat().export_data(dataset), content_type=ExcelFormat.CONTENT_TYPE
        )
        name = slugify(str(self.opts.verbose_name_plural))
        response["Content-Disposition"] = f'attachment; filename="{name}-namuna.xlsx"'
        return response

    def add_data_read_fail_error_to_form(self, form, e):
        if isinstance(e, SheetError):
            message = str(e)
        elif isinstance(e, UnicodeDecodeError):
            message = (
                "CSV faylning kodlashi UTF-8 emas. Excel'da “Saqlash: CSV UTF-8” bilan saqlang "
                "yoki .xlsx yuklang."
            )
        else:
            message = "Faylni o‘qib bo‘lmadi. Fayl buzilmaganini va turi to‘g‘riligini tekshiring."
        form.add_error("import_file", message)

    def process_result(self, result, request):
        if result.has_errors() or result.has_validation_errors():
            messages.error(
                request,
                "Tekshiruvdan keyin bazadagi ma’lumot o‘zgardi, shuning uchun hech narsa "
                "saqlanmadi. Faylni qayta yuklang.",
            )
            return redirect("admin:{}_{}_import".format(*self.get_model_info()))
        return super().process_result(result, request)

    def add_success_message(self, result, request):
        totals = result.totals
        messages.success(
            request,
            f"Saqlandi: yangi {totals[RowResult.IMPORT_TYPE_NEW]} ta, yangilandi "
            f"{totals[RowResult.IMPORT_TYPE_UPDATE]} ta, o‘zgarmadi "
            f"{totals[RowResult.IMPORT_TYPE_SKIP]} ta.",
        )

    def _create_log_entry(self, user_pk, rows, import_type, action_flag):
        if rows:
            LogEntry.objects.log_actions(
                user_pk,
                rows,
                action_flag,
                change_message="Fayldan yuklandi.",
                single_object=len(rows) == 1,
            )

    # ------------------------------------------------------------------------------ export

    def get_export_data(self, file_format, request, queryset, **kwargs):
        # Excel opens a UTF-8 CSV correctly only with the byte order mark; JSON must not have one.
        kwargs["encoding"] = "utf-8-sig" if isinstance(file_format, CsvFormat) else "utf-8"
        return super().get_export_data(file_format, request, queryset, **kwargs)

    def get_export_filename(self, request, queryset, file_format):
        name = slugify(str(self.opts.verbose_name_plural))
        return f"{name}-{timezone.localdate():%Y-%m-%d}.{file_format.get_extension()}"

    def init_request_context_data(self, request, form):
        context = super().init_request_context_data(request, form)
        context["title"] = f"{capfirst(self.opts.verbose_name_plural)}: yuklab olish"
        context["export_count"] = self.get_export_queryset(request).count()
        return context
