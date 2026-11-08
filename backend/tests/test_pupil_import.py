"""Bulk pupil import from Excel/CSV (accounts.pupil_import) and its admin page."""

import io
import zipfile

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts import pupil_import
from apps.accounts.models import Pupil, hash_imie
from apps.accounts.pupil_import import (
    ImportFileError,
    apply_import,
    build_template,
    plan_import,
    read_rows,
)
from apps.schools.models import Classroom

from .conftest import ALIYA_JSHSHIR, client_for, make_classroom

pytestmark = pytest.mark.django_db

HEADER = "Sinf;Familiya;Ism;Otasining ismi;JSHSHIR"


def csv_file(*lines: str, name="list.csv", encoding="utf-8") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, "\n".join(lines).encode(encoding))


def xlsx_file(rows: list[list], name="list.xlsx") -> SimpleUploadedFile:
    workbook = openpyxl.Workbook()
    for row in rows:
        workbook.active.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(name, buffer.getvalue())


def read(*lines: str):
    return read_rows(csv_file(HEADER, *lines))


def messages(errors) -> list[str]:
    return [f"{error.line}: {error.message}" for error in errors]


class TestReading:
    def test_csv_with_semicolons_and_excel_bom(self):
        upload = SimpleUploadedFile(
            "a.csv", ("﻿" + HEADER + "\n5-A;Karimov;Aziz;Rustamovich;12345678901234").encode()
        )
        rows, errors = read_rows(upload)
        assert errors == []
        row = rows[0]
        assert (row.grade, row.category, row.last_name, row.first_name, row.middle_name) == (
            5,
            "A",
            "Karimov",
            "Aziz",
            "Rustamovich",
        )
        assert row.imie_hash == hash_imie("12345678901234")
        assert "12345678901234" not in repr(row)  # only the hash travels on

    def test_csv_with_commas(self):
        rows, errors = read_rows(
            csv_file("sinf,familiya,ism,jshshir", "6b,Aliyev,Bobur,34567890123456")
        )
        assert errors == [] and rows[0].classroom_label == "6-B"

    def test_xlsx_with_numbers_a_title_row_and_other_header_spellings(self):
        upload = xlsx_file(
            [
                ["12-maktab o‘quvchilari ro‘yxati"],
                [],
                ["№", "Familiyasi", "Ismi", "Sharifi", "PINFL", "Sinfi"],
                [1, "Yusupova", "Malika", "Akmalovna", 23456789012345, "5 «a»"],
                [2, "Karimov", "Aziz", None, 12345678901234.0, "11-B"],
                [None, None, None, None, None, None],
            ]
        )
        rows, errors = read_rows(upload)
        assert errors == []
        assert [(r.line, r.classroom_label, r.middle_name) for r in rows] == [
            (4, "5-A", "Akmalovna"),
            (5, "11-B", ""),
        ]
        assert rows[1].imie_hash == hash_imie("12345678901234")

    def test_extra_spaces_are_cleaned(self):
        rows, _ = read("  5-A ;  Karimov  ; Aziz   Bek ;; 1234 5678 9012 34")
        assert (rows[0].first_name, rows[0].imie_hash) == ("Aziz Bek", hash_imie("12345678901234"))

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("5-A;;Aziz;;12345678901234", "Familiya yozilmagan"),
            ("5-A;Karimov;;;12345678901234", "Ism yozilmagan"),
            (";Karimov;Aziz;;12345678901234", "Sinf yozilmagan"),
            ("5-А;Karimov;Aziz;;12345678901234", "lotin alifbosida"),  # Cyrillic А
            ("beshinchi;Karimov;Aziz;;12345678901234", "tushunilmadi"),
            ("12-A;Karimov;Aziz;;12345678901234", "1 dan 11 gacha"),
            ("5-A;Karimov;Aziz;;1234567890123", "14 ta raqam"),
            ("5-A;Karimov;Aziz;;3,12346E+13", "songa aylantirib buzgan"),
            ("5-A;" + "K" * 101 + ";Aziz;;12345678901234", "juda uzun"),
        ],
    )
    def test_row_problems_are_reported_with_the_line(self, line, expected):
        rows, errors = read(line)
        assert rows == []
        assert len(errors) == 1 and errors[0].line == 2 and expected in errors[0].message

    def test_one_row_can_have_several_problems(self):
        _, errors = read(";;;;abc")  # a row of nothing but ";" is skipped as empty
        assert len(errors) == 4  # class, last name, first name, JSHSHIR

    def test_error_message_never_shows_the_number(self):
        _, errors = read("5-A;Karimov;Aziz;;12345678901234", "5-B;Boshqa;Ism;;12345678901234")
        assert messages(errors) == ["3: JSHSHIR 2-qatordagi bilan bir xil."]

    @pytest.mark.parametrize(
        ("upload", "expected"),
        [
            (csv_file("a;b;c", "1;2;3"), "Sarlavha qatori topilmadi"),
            (csv_file(HEADER), "birorta ham o‘quvchi yo‘q"),
            (csv_file("Sinf;Ism;Ism;Familiya;JSHSHIR"), "ikki marta"),
            (csv_file(HEADER, "5-A;O‘g‘iloy;Ism;;12345678901234", encoding="utf-16"), "UTF-8"),
            (SimpleUploadedFile("list.xls", b"old"), ".xls"),
            (SimpleUploadedFile("list.pdf", b"%PDF"), "Faqat .xlsx yoki .csv"),
            (SimpleUploadedFile("list.xlsx", b"not a zip"), "buzilgan"),
        ],
    )
    def test_unusable_files(self, upload, expected):
        with pytest.raises(ImportFileError, match=expected):
            read_rows(upload)

    def test_too_big_file(self, monkeypatch):
        monkeypatch.setattr(pupil_import, "MAX_FILE_BYTES", 10)
        with pytest.raises(ImportFileError, match="juda katta"):
            read_rows(csv_file(HEADER))

    def test_too_many_rows(self, monkeypatch):
        monkeypatch.setattr(pupil_import, "MAX_ROWS", 2)
        lines = [f"5-A;F;I;;{n:014d}" for n in range(1, 4)]
        with pytest.raises(ImportFileError, match="2 tadan ko‘p"):
            read(*lines)

    def test_xlsx_that_unpacks_into_too_much_data(self, monkeypatch):
        monkeypatch.setattr(pupil_import, "MAX_UNPACKED_BYTES", 1000)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/sharedStrings.xml", "A" * 5000)  # compresses to a few bytes
        with pytest.raises(ImportFileError, match="juda katta"):
            read_rows(SimpleUploadedFile("bomb.xlsx", buffer.getvalue()))


class TestPlanAndApply:
    def rows(self, *lines: str):
        rows, errors = read(*lines)
        assert errors == []
        return rows

    def test_new_pupils_and_classes(self, db):
        school = make_classroom().school  # has 5-A
        rows = self.rows("5-A;Karimov;Aziz;;12345678901234", "6-B;Aliyev;Bobur;;34567890123456")

        plan = plan_import(school, rows, create_classrooms=True)
        assert (len(plan.created), plan.new_classrooms) == (2, ["6-B"])
        assert not Pupil.objects.exists()  # planning saves nothing

        apply_import(school.pk, rows, create_classrooms=True)
        new_class = Classroom.objects.get(school=school, number=6, category="B")
        assert (new_class.name, new_class.count) == ("6-B", 1)
        assert Pupil.objects.get(imie_hash=hash_imie("34567890123456")).classroom == new_class
        login = client_for().post("/api/auth/jshshir", {"jshshir": "12345678901234"}, format="json")
        assert login.status_code == 200

    def test_missing_class_is_an_error_when_classes_may_not_be_created(self, db):
        school = make_classroom().school
        plan = plan_import(school, self.rows("7-V;A;B;;12345678901234"), create_classrooms=False)
        assert messages(plan.errors) == ["2: Bu maktabda 7-V sinfi yo‘q."]

    def test_existing_pupil_is_updated_not_duplicated(self, aliya):
        make_classroom(number=6, category="A")
        rows = self.rows(f"6-A;Yangi familiya;Aliya;Karimovna;{ALIYA_JSHSHIR}")
        plan = apply_import(aliya.classroom.school_id, rows, create_classrooms=False)
        assert (len(plan.created), len(plan.updated)) == (0, 1)
        aliya.refresh_from_db()
        assert (aliya.last_name, aliya.middle_name, aliya.classroom.name) == (
            "Yangi familiya",
            "Karimovna",
            "6-A",
        )
        assert Pupil.objects.count() == 1

    def test_same_data_again_changes_nothing(self, aliya):
        rows = self.rows(f"5-A;Test;Aliya;;{ALIYA_JSHSHIR}")
        plan = plan_import(aliya.classroom.school, rows, create_classrooms=False)
        assert (plan.unchanged, plan.has_changes) == (1, False)

    def test_pupil_from_another_school_is_moved_and_reported(self, aliya):
        other = make_classroom(school_number=2).school
        rows = self.rows(f"5-A;Test;Aliya;;{ALIYA_JSHSHIR}")
        plan = plan_import(other, rows, create_classrooms=True)
        assert [(row.full_name, old) for row, old in plan.moved] == [
            ("Test Aliya", "1-maktab (Tuman)")
        ]
        apply_import(other.pk, rows, create_classrooms=True)
        aliya.refresh_from_db()
        assert aliya.classroom.school == other

    def test_pupils_missing_from_the_file_are_left_alone(self, aliya, bek):
        apply_import(aliya.classroom.school_id, self.rows("5-A;New;One;;12345678901234"), False)
        assert Pupil.objects.count() == 3

    def test_status_of_existing_pupils_is_not_changed(self, aliya):
        Pupil.objects.filter(pk=aliya.pk).update(status=False)
        apply_import(aliya.classroom.school_id, self.rows(f"5-A;X;Aliya;;{ALIYA_JSHSHIR}"), False)
        aliya.refresh_from_db()
        assert aliya.status is False

    def test_graduated_class_is_not_reused(self, db):
        old = make_classroom(number=11, category="A")
        Classroom.objects.filter(pk=old.pk).update(graduated_year=2025, status=False)
        apply_import(old.school_id, self.rows("11-A;New;One;;12345678901234"), True)
        pupil = Pupil.objects.get()
        assert pupil.classroom != old and pupil.classroom.graduated_year is None

    def test_plan_is_checked_again_when_saving(self, db):
        school = make_classroom().school
        rows = self.rows("8-A;New;One;;12345678901234")
        assert plan_import(school, rows, create_classrooms=False).ok is False
        plan = apply_import(school.pk, rows, create_classrooms=False)
        assert not plan.ok and not Pupil.objects.exists()

    def test_many_pupils_take_a_fixed_number_of_queries(self, db, django_assert_max_num_queries):
        school = make_classroom().school
        rows = self.rows(*[f"{5 + n % 3}-A;F{n};I{n};;{n + 1:014d}" for n in range(300)])
        with django_assert_max_num_queries(10):
            apply_import(school.pk, rows, create_classrooms=True)
        assert Pupil.objects.count() == 300


class TestTemplate:
    def test_template_can_be_read_back(self):
        rows, errors = read_rows(SimpleUploadedFile("t.xlsx", build_template()))
        assert errors == [] and rows[0].classroom_label == "5-A"

    def test_jshshir_column_is_text(self):
        sheet = openpyxl.load_workbook(io.BytesIO(build_template())).active
        assert sheet["E2"].number_format == "@" and sheet["E2"].value == "12345678901234"


class TestAdminPage:
    @pytest.fixture
    def staff(self, client):
        client.force_login(get_user_model().objects.create_superuser("admin", password="x"))
        return client

    @pytest.fixture
    def school(self, db):
        return make_classroom().school

    def url(self, school):
        return f"/admin/schools/school/{school.pk}/import-pupils/"

    def upload(self, staff, school, *lines, create=True):
        data = {"file": csv_file(HEADER, *lines)}
        if create:
            data["create_classrooms"] = "on"
        return staff.post(self.url(school), data)

    def test_school_page_has_the_button(self, staff, school):
        page = staff.get(f"/admin/schools/school/{school.pk}/change/").content.decode()
        assert self.url(school) in page

    def test_upload_then_confirm(self, staff, school):
        preview = self.upload(staff, school, "6-B;Karimov;Aziz;;12345678901234")
        page = preview.content.decode()
        assert "Tasdiqlash va saqlash" in page and "Karimov Aziz" in page
        assert not Pupil.objects.exists()

        token = preview.context["token"]
        response = staff.post(self.url(school), {"confirm": "1", "token": token})
        assert response.status_code == 302
        assert Pupil.objects.get().classroom.name == "6-B"
        # The pending rows are gone, so a second click doesn't import again.
        again = staff.post(self.url(school), {"confirm": "1", "token": token}, follow=True)
        assert "eskirgan" in again.content.decode()

    def test_session_never_holds_the_number(self, staff, school):
        self.upload(staff, school, "6-B;Karimov;Aziz;;12345678901234")
        assert "12345678901234" not in str(dict(staff.session))

    def test_errors_show_and_there_is_no_confirm_button(self, staff, school):
        page = self.upload(staff, school, "6-B;;Aziz;;12345678901234").content.decode()
        assert "Familiya yozilmagan" in page
        assert "Tasdiqlash va saqlash" not in page

    def test_bad_file_returns_to_the_form_with_the_reason(self, staff, school):
        response = staff.post(self.url(school), {"file": SimpleUploadedFile("a.pdf", b"x")})
        assert "Faqat .xlsx yoki .csv" in response.content.decode()

    def test_token_from_another_school_is_refused(self, staff, school):
        preview = self.upload(staff, school, "6-B;Karimov;Aziz;;12345678901234")
        other = make_classroom(school_number=2).school
        staff.post(self.url(other), {"confirm": "1", "token": preview.context["token"]})
        assert not Pupil.objects.exists()

    def test_template_download(self, staff):
        response = staff.get("/admin/schools/school/import-pupils/template.xlsx")
        assert response.status_code == 200
        assert response["Content-Disposition"].endswith('.xlsx"')

    def test_staff_without_pupil_permissions_is_refused(self, client, school):
        user = get_user_model().objects.create_user("viewer", password="x", is_staff=True)
        client.force_login(user)
        assert client.get(self.url(school)).status_code == 403
        assert client.get("/admin/schools/school/import-pupils/template.xlsx").status_code == 403

    def test_change_is_written_to_the_history(self, staff, school):
        preview = self.upload(staff, school, "6-B;Karimov;Aziz;;12345678901234")
        staff.post(self.url(school), {"confirm": "1", "token": preview.context["token"]})
        history = staff.get(f"/admin/schools/school/{school.pk}/history/").content.decode()
        assert "fayldan yuklandi" in history
