"""
Bulk import of one school's pupil list from Excel (.xlsx) or CSV.

Three steps, used by the "O'quvchilarni yuklash" page on a school in the admin:
  1. read_rows(file)            reads and checks every row; nothing is saved
  2. plan_import(school, rows)  works out what would change, for the preview page
  3. apply_import(school, rows) plans again inside a transaction and saves: all rows or none

A row keeps only the IMIE hash, never the number itself, so the checked rows can wait in the
admin's session between the preview and the confirmation.

Matching is by IMIE. A pupil who is already in the database is updated (name, class) and, if they
were in another school, moved here. Pupils who are missing from the file are left alone.
"""

import csv
import io
import re
import zipfile
from dataclasses import dataclass, field

from django.db import transaction

from apps.schools.models import FINAL_GRADE, Classroom, School

from .models import Pupil, hash_imie

MAX_FILE_BYTES = 5 * 1024 * 1024
# An .xlsx is a zip. A small file can unpack into gigabytes, so the unpacked size is checked
# before Excel's reader ever opens it.
MAX_UNPACKED_BYTES = 50 * 1024 * 1024
MAX_ROWS = 5000
HEADER_SEARCH_ROWS = 10  # a file may start with a title like "12-maktab o'quvchilari"

# Column -> accepted header spellings, compared after dropping everything but letters.
COLUMNS = {
    "classroom": ("sinf", "sinfi", "класс"),
    "last_name": ("familiya", "familiyasi", "фамилия"),
    "first_name": ("ism", "ismi", "имя"),
    "middle_name": ("otasiningismi", "sharif", "sharifi", "отчество"),
    "imie": ("jshshir", "jshshr", "pinfl", "imie", "жшшир"),
}
REQUIRED = ("classroom", "last_name", "first_name", "imie")
TEMPLATE_HEADERS = ["Sinf", "Familiya", "Ism", "Otasining ismi", "JSHSHIR"]

CLASSROOM_PATTERN = re.compile(r"^(\d{1,2})\s*[-–—]?\s*[\"'«]?([A-Za-z]{1,3})[\"'»]?$")
CYRILLIC = re.compile(r"[Ѐ-ӿ]")
SCIENTIFIC = re.compile(r"^\d([.,]\d+)?[eE]\+?\d+$")


class ImportFileError(Exception):
    """The whole file is unusable: wrong format, too big, no header row."""


@dataclass(frozen=True)
class PupilRow:
    line: int
    grade: int
    category: str
    last_name: str
    first_name: str
    middle_name: str
    imie_hash: str

    @property
    def classroom_label(self) -> str:
        return f"{self.grade}-{self.category}"

    @property
    def full_name(self) -> str:
        return " ".join(filter(None, [self.last_name, self.first_name, self.middle_name]))


@dataclass(frozen=True)
class RowError:
    line: int
    message: str


@dataclass
class ImportPlan:
    new_classrooms: list[str] = field(default_factory=list)
    created: list[PupilRow] = field(default_factory=list)
    updated: list[PupilRow] = field(default_factory=list)
    # (row, name of the school the pupil is in now)
    moved: list[tuple[PupilRow, str]] = field(default_factory=list)
    unchanged: int = 0
    errors: list[RowError] = field(default_factory=list)
    # What apply_import needs to save; not shown anywhere.
    _changes: list[tuple[Pupil, PupilRow]] = field(default_factory=list, repr=False)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def has_changes(self) -> bool:
        return bool(self.new_classrooms or self.created or self.updated or self.moved)


# ------------------------------------------------------------------------------------ reading


def read_rows(uploaded) -> tuple[list[PupilRow], list[RowError]]:
    """Raises ImportFileError for a bad file; problems in single rows come back as RowErrors."""
    table = _read_table(uploaded)
    header_index, columns = _find_header(table)

    rows: list[PupilRow] = []
    errors: list[RowError] = []
    first_line_of: dict[str, int] = {}
    for index in range(header_index + 1, len(table)):
        cells = table[index]
        if not any(cells):
            continue
        line = index + 1  # the row number Excel shows
        values = {name: cells[col] if col < len(cells) else "" for name, col in columns.items()}
        row, problems = _parse_row(line, values)
        if row is not None and row.imie_hash in first_line_of:
            problems.append(f"JSHSHIR {first_line_of[row.imie_hash]}-qatordagi bilan bir xil.")
        if problems:
            errors.extend(RowError(line, problem) for problem in problems)
        elif row is not None:
            first_line_of[row.imie_hash] = line
            rows.append(row)

    if not rows and not errors:
        raise ImportFileError("Faylda sarlavhadan keyin birorta ham o‘quvchi yo‘q.")
    return rows, errors


def _read_table(uploaded) -> list[list[str]]:
    if uploaded.size > MAX_FILE_BYTES:
        megabytes = MAX_FILE_BYTES // (1024 * 1024)
        raise ImportFileError(f"Fayl juda katta: {megabytes} MB dan oshmasin.")
    name = uploaded.name.lower()
    if name.endswith(".xlsx"):
        table = _read_xlsx(uploaded)
    elif name.endswith(".csv"):
        table = _read_csv(uploaded)
    elif name.endswith(".xls"):
        raise ImportFileError(
            "Eski .xls formati o‘qilmaydi. Excel'da: Fayl → Saqlash → “Excel kitobi (.xlsx)”."
        )
    else:
        raise ImportFileError("Faqat .xlsx yoki .csv fayl yuklang.")

    filled = [row for row in table if any(row)]
    if len(filled) > MAX_ROWS + 1:
        raise ImportFileError(f"Bir faylda {MAX_ROWS} tadan ko‘p qator bo‘lmasin.")
    return table


def _read_xlsx(uploaded) -> list[list[str]]:
    # Imported here: openpyxl is big, and only this admin page needs it.
    import openpyxl

    try:
        with zipfile.ZipFile(uploaded) as archive:
            unpacked = sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile as error:
        raise ImportFileError("Fayl Excel (.xlsx) emas yoki buzilgan.") from error
    if unpacked > MAX_UNPACKED_BYTES:
        raise ImportFileError("Excel fayl ichidagi ma’lumot juda katta.")

    uploaded.seek(0)
    try:
        workbook = openpyxl.load_workbook(uploaded, read_only=True, data_only=True)
    except Exception as error:  # openpyxl raises many kinds of errors for a broken file
        raise ImportFileError("Excel faylni o‘qib bo‘lmadi. U buzilgan bo‘lishi mumkin.") from error
    try:
        table, filled = [], 0
        for values in workbook.worksheets[0].iter_rows(values_only=True):
            cells = [_cell(value) for value in values]
            table.append(cells)
            filled += any(cells)
            if filled > MAX_ROWS + 1:
                break  # enough to report "too many rows" without reading the rest
        return table
    finally:
        workbook.close()


def _read_csv(uploaded) -> list[list[str]]:
    raw = uploaded.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        # Guessing another encoding would quietly turn "O‘g‘iloy" into garbage, so refuse instead.
        raise ImportFileError(
            "CSV fayl UTF-8 kodlashda emas. Excel'da “CSV UTF-8” sifatida saqlang "
            "yoki .xlsx yuklang."
        ) from error
    first_line = text.split("\n", 1)[0]
    # Excel uses ";" in many locales (including Uzbek and Russian), "," elsewhere.
    delimiter = max(";,\t", key=first_line.count)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    return [[_cell(value) for value in row] for row in reader]


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # Excel keeps every number as a float: 31234567890123.0
    return " ".join(str(value).split())


def _header_key(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalpha())


def _find_header(table: list[list[str]]) -> tuple[int, dict[str, int]]:
    spellings = {spelling: name for name, options in COLUMNS.items() for spelling in options}
    for index, cells in enumerate(table[:HEADER_SEARCH_ROWS]):
        columns: dict[str, int] = {}
        for position, cell in enumerate(cells):
            name = spellings.get(_header_key(cell))
            if name is None:
                continue
            if name in columns:
                raise ImportFileError(f"“{cell}” ustuni ikki marta yozilgan.")
            columns[name] = position
        if all(name in columns for name in REQUIRED):
            return index, columns
    raise ImportFileError(
        "Sarlavha qatori topilmadi. Ustunlar: " + ", ".join(TEMPLATE_HEADERS) + ". Namuna faylni "
        "yuklab olib, shunga moslang."
    )


def _parse_row(line: int, values: dict[str, str]) -> tuple[PupilRow | None, list[str]]:
    problems = []

    grade, category = _parse_classroom(values["classroom"], problems)

    names = {}
    for key, label, required in [
        ("last_name", "Familiya", True),
        ("first_name", "Ism", True),
        ("middle_name", "Otasining ismi", False),
    ]:
        value = values.get(key, "")
        if required and not value:
            problems.append(f"{label} yozilmagan.")
        elif len(value) > 100:
            problems.append(f"{label} juda uzun (100 belgidan oshmasin).")
        names[key] = value

    imie = values["imie"].replace(" ", "")
    if SCIENTIFIC.match(imie):
        problems.append(
            "Excel JSHSHIRni songa aylantirib buzgan (masalan 3,12E+13). Ustun formatini “Matn” "
            "qilib, raqamlarni qayta kiriting."
        )
    elif not re.fullmatch(r"\d{14}", imie):
        problems.append("JSHSHIR 14 ta raqamdan iborat bo‘lishi kerak.")

    if problems:
        return None, problems
    return PupilRow(line, grade, category, **names, imie_hash=hash_imie(imie)), []


def _parse_classroom(value: str, problems: list[str]) -> tuple[int, str]:
    match = CLASSROOM_PATTERN.match(value)
    if not match:
        if not value:
            problems.append("Sinf yozilmagan.")
        elif CYRILLIC.search(value):
            problems.append(f"Sinf “{value}”: harfni lotin alifbosida yozing, masalan 5-A.")
        else:
            problems.append(f"Sinf “{value}” tushunilmadi. Masalan: 5-A.")
        return 0, ""
    grade, category = int(match[1]), match[2].upper()
    if not 1 <= grade <= FINAL_GRADE:
        problems.append(f"Sinf raqami 1 dan {FINAL_GRADE} gacha bo‘lishi kerak.")
    return grade, category


# ----------------------------------------------------------------------------------- planning


def plan_import(
    school: School, rows: list[PupilRow], create_classrooms: bool, errors: list[RowError] = ()
) -> ImportPlan:
    plan = ImportPlan(errors=list(errors))
    classrooms = {(c.number, c.category): c for c in school.classrooms.current()}

    missing = sorted({(row.grade, row.category) for row in rows} - classrooms.keys())
    if create_classrooms:
        plan.new_classrooms = [f"{grade}-{category}" for grade, category in missing]
    else:
        missing_set = set(missing)
        plan.errors += [
            RowError(row.line, f"Bu maktabda {row.classroom_label} sinfi yo‘q.")
            for row in rows
            if (row.grade, row.category) in missing_set
        ]

    existing = {
        pupil.imie_hash: pupil
        for pupil in Pupil.objects.filter(
            imie_hash__in=[row.imie_hash for row in rows]
        ).select_related("classroom__school")
    }
    for row in rows:
        pupil = existing.get(row.imie_hash)
        if pupil is None:
            plan.created.append(row)
        elif pupil.classroom.school_id != school.pk:
            plan.moved.append((row, str(pupil.classroom.school)))
            plan._changes.append((pupil, row))
        elif _differs(pupil, row):
            plan.updated.append(row)
            plan._changes.append((pupil, row))
        else:
            plan.unchanged += 1

    plan.errors.sort(key=lambda error: error.line)
    return plan


def _differs(pupil: Pupil, row: PupilRow) -> bool:
    classroom = pupil.classroom
    return (
        classroom.graduated_year is not None
        or (classroom.number, classroom.category) != (row.grade, row.category)
        or (pupil.last_name, pupil.first_name, pupil.middle_name)
        != (row.last_name, row.first_name, row.middle_name)
    )


# ------------------------------------------------------------------------------------- saving


def apply_import(school_id: int, rows: list[PupilRow], create_classrooms: bool) -> ImportPlan:
    """
    Plans again before saving, because the database may have changed since the preview.
    If that new plan has errors, nothing is saved and the plan is returned so they can be shown.
    """
    with transaction.atomic():
        # Locks the school, so an import and a yearly promotion never run at the same time.
        school = School.objects.select_for_update().get(pk=school_id)
        plan = plan_import(school, rows, create_classrooms)
        if not plan.ok:
            return plan

        classrooms = {(c.number, c.category): c for c in school.classrooms.current()}
        sizes: dict[tuple[int, str], int] = {}
        for row in rows:
            sizes[(row.grade, row.category)] = sizes.get((row.grade, row.category), 0) + 1
        new = [
            Classroom(
                school=school,
                number=grade,
                category=category,
                name=f"{grade}-{category}",
                count=sizes[(grade, category)],
            )
            for grade, category in sizes
            if (grade, category) not in classrooms
        ]
        for classroom in Classroom.objects.bulk_create(new):
            classrooms[(classroom.number, classroom.category)] = classroom

        Pupil.objects.bulk_create(
            [
                Pupil(
                    classroom=classrooms[(row.grade, row.category)],
                    last_name=row.last_name,
                    first_name=row.first_name,
                    middle_name=row.middle_name,
                    imie_hash=row.imie_hash,
                )
                for row in plan.created
            ],
            batch_size=500,
        )

        for pupil, row in plan._changes:
            pupil.classroom = classrooms[(row.grade, row.category)]
            pupil.last_name, pupil.first_name = row.last_name, row.first_name
            pupil.middle_name = row.middle_name
        Pupil.objects.bulk_update(
            [pupil for pupil, _ in plan._changes],
            ["classroom", "last_name", "first_name", "middle_name"],
            batch_size=500,
        )
    return plan


def build_template() -> bytes:
    """The sample file offered on the import page. The JSHSHIR column is text, so Excel keeps it."""
    import openpyxl

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "O‘quvchilar"
    sheet.append(TEMPLATE_HEADERS)
    sheet.append(["5-A", "Karimov", "Aziz", "Rustamovich", "12345678901234"])
    for column, width in zip("ABCDE", [8, 20, 20, 22, 18], strict=True):
        sheet.column_dimensions[column].width = width
    for cell in sheet["E"]:
        cell.number_format = "@"
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
