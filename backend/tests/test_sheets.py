"""Admin file import and export of regions, districts, schools and questions (apps/core/sheets)."""

import io
import json
import zipfile

import openpyxl
import pytest
import tablib
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core import sheets
from apps.core.sheets import ExcelFormat, name_key, summary, to_html
from apps.exams.models import AnswerOption, Question
from apps.exams.services import start_attempt
from apps.schools.models import District, Region, School

from .conftest import make_exam, make_pupil, text

pytestmark = pytest.mark.django_db

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def staff(client):
    user = get_user_model().objects.create_superuser("admin", password="pass-for-tests")
    client.force_login(user)
    return client


def xlsx(headers, *rows, name="file.xlsx") -> SimpleUploadedFile:
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=XLSX)


def read_xlsx(content: bytes) -> list[list]:
    sheet = openpyxl.load_workbook(io.BytesIO(content)).active
    return [[cell.value for cell in row] for row in sheet.iter_rows()]


def check(client, model: str, upload, **fields):
    """Step 2: upload a file. Nothing is saved yet; the response shows what would change."""
    # A browser always sends the form's hidden fields too; the view needs a non-empty POST.
    return client.post(
        f"/admin/{model}/import/", {"import_file": upload, "resource": "0", **fields}
    )


def confirm(client, model: str, checked):
    form = checked.context["confirm_form"]
    data = {name: field.initial for name, field in form.fields.items()}
    data.update({name: value for name, value in form.initial.items()})
    return client.post(f"/admin/{model}/process_import/", data)


def export(client, url: str, file_format: str, **kwargs):
    """Posts the export form as a browser would: every column ticked, as the page starts."""
    form = client.get(url).context["form"]
    data = {
        name: "on"
        for name, field in form.fields.items()
        if getattr(field, "is_selectable_field", False)
    }
    return client.post(url, {**data, "format": file_format, "resource": "0"}, **kwargs)


def errors_of(response) -> list[tuple]:
    """(file line, column, message) for every problem the check page lists."""
    result = response.context["result"]
    found = [(None, None, str(error.error)) for error in result.base_errors]
    for row in result.invalid_rows:
        for column, messages in row.error_dict.items():
            found += [(row.number + 1, column, message) for message in messages]
    return found


def totals(response) -> dict:
    result = response.context["result"]
    return {key: result.totals[key] for key in ("new", "update", "skip")}


@pytest.fixture
def regions(db):
    andijon = Region.objects.create(number=2, name="Andijon viloyati")
    fargona = Region.objects.create(number=4, name="Farg‘ona viloyati")
    return andijon, fargona


class TestTextFromCells:
    def test_names_compare_without_apostrophe_case_and_space_differences(self):
        assert name_key("Farg'ona  viloyati ") == name_key("FARGʻONA viloyati")
        assert name_key("Farg‘ona") == name_key("Fargʼona")

    def test_plain_text_becomes_paragraphs_and_is_escaped(self):
        assert to_html("Birinchi qator\n\n  ikkinchi   qator ") == (
            "<p>Birinchi qator</p><p>ikkinchi qator</p>"
        )
        assert to_html("3 < 5 va 7 > 2") == "<p>3 &lt; 5 va 7 &gt; 2</p>"

    def test_comparisons_inside_formulas_are_not_taken_for_tags(self):
        assert to_html("$a<b$ va $c>d$") == "<p>$a&lt;b$ va $c&gt;d$</p>"

    def test_editor_html_is_kept_as_it_is(self):
        assert to_html("<p>Hisoblang: <b>2+3</b></p>") == "<p>Hisoblang: <b>2+3</b></p>"

    def test_numbers_from_excel(self):
        assert to_html(12.0) == "<p>12</p>"

    def test_summary_hides_markup_and_pictures(self):
        picture = '<figure class="image"><img src="data:image/webp;base64,AAAA"></figure>'
        value = f"<p>Soat <b>necha</b>?</p>{picture}"
        assert summary(value) == "Soat necha? [rasm]"
        assert summary("x" * 300, limit=10) == "xxxxxxxxx…"


class TestExcelFile:
    def test_text_that_looks_like_a_formula_stays_text(self):
        dataset = tablib.Dataset(["=2+3", 5], headers=["Matn", "Son"])
        rows = read_xlsx(ExcelFormat().export_data(dataset))
        assert rows == [["Matn", "Son"], ["=2+3", 5]]

    def test_value_too_long_for_a_cell_stops_the_export(self):
        dataset = tablib.Dataset(["x" * 40_000], headers=["Savol matni"])
        with pytest.raises(ValueError, match="JSON formatida"):
            ExcelFormat().export_data(dataset)

    def test_blank_rows_and_header_spaces_are_ignored(self):
        upload = xlsx([" Nomi ", "Raqami"], ["A", 1], [None, None], ["B", 2])
        dataset = ExcelFormat().create_dataset(upload.read())
        assert dataset.headers == ["Nomi", "Raqami"]
        assert len(dataset) == 2

    def test_file_that_unpacks_into_too_much_data(self, monkeypatch):
        monkeypatch.setattr(sheets, "MAX_UNPACKED_BYTES", 1000)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/sharedStrings.xml", "A" * 5000)
        with pytest.raises(sheets.SheetError, match="juda katta"):
            ExcelFormat().create_dataset(buffer.getvalue())


class TestRegions:
    def test_new_and_changed_rows_are_shown_then_saved_on_confirm(self, staff, regions):
        upload = xlsx(
            ["Raqami", "Nomi", "Faol"], [2, "Andijon viloyati", "yo‘q"], [5, "Buxoro viloyati", ""]
        )
        checked = check(staff, "schools/region", upload)
        assert checked.status_code == 200
        assert totals(checked) == {"new": 1, "update": 1, "skip": 0}
        assert not Region.objects.filter(number=5).exists()  # only checked so far

        response = confirm(staff, "schools/region", checked)
        assert response.status_code == 302
        assert Region.objects.get(number=5).status is True  # empty "Faol": a new one is active
        assert Region.objects.get(number=2).status is False

    def test_exported_file_comes_back_unchanged(self, staff, regions):
        exported = export(staff, "/admin/schools/region/export/", "0")
        assert exported.status_code == 200
        assert exported["Content-Disposition"].endswith('.xlsx"')
        rows = read_xlsx(exported.content)
        assert rows[0] == ["Raqami", "Nomi", "Faol"]
        assert rows[1:] == [[2, "Andijon viloyati", "ha"], [4, "Farg‘ona viloyati", "ha"]]

        checked = check(staff, "schools/region", SimpleUploadedFile("back.xlsx", exported.content))
        assert totals(checked) == {"new": 0, "update": 0, "skip": 2}
        assert "confirm_form" in checked.context
        assert "saqlanadigan narsa yo‘q" in checked.content.decode()

    def test_csv_export_opens_in_excel(self, staff, regions):
        exported = export(staff, "/admin/schools/region/export/", "1")
        assert exported.content.startswith("﻿".encode())  # without it Excel garbles ‘ and ʻ
        assert "Farg‘ona viloyati" in exported.content.decode("utf-8-sig")

    def test_export_keeps_the_list_filter(self, staff, regions):
        Region.objects.filter(number=4).update(status=False)
        exported = export(staff, "/admin/schools/region/export/?status__exact=1", "0")
        assert [row[0] for row in read_xlsx(exported.content)[1:]] == [2]

    def test_bad_row_saves_nothing_and_names_the_row_and_column(self, staff, regions):
        upload = xlsx(["Raqami", "Nomi", "Faol"], [7, "Yangi", "ha"], ["yetti", "Boshqa", "balki"])
        checked = check(staff, "schools/region", upload)
        found = errors_of(checked)
        assert (3, "Raqami", "“yetti”: butun son yozing, masalan 5.") in found
        assert (3, "Faol", "“balki”: “ha” yoki “yo‘q” deb yozing.") in found
        assert "confirm_form" not in checked.context
        assert not Region.objects.filter(number=7).exists()

    def test_same_record_twice_in_one_file(self, staff, regions):
        upload = xlsx(["Raqami", "Nomi"], [9, "Bir"], [9, "Ikki"])
        found = errors_of(check(staff, "schools/region", upload))
        assert any(line == 3 and "2-qatorda ham" in message for line, _, message in found)

    def test_missing_required_column(self, staff, regions):
        found = errors_of(check(staff, "schools/region", xlsx(["Nomi"], ["Bir"])))
        assert found == [
            (
                None,
                None,
                "Faylda kerakli ustun yo‘q: “Raqami”. Ustun nomlari namuna fayldagidek bo‘lsin.",
            )
        ]

    def test_header_spelling_does_not_matter(self, staff, regions):
        checked = check(staff, "schools/region", xlsx(["raqami", "NOMI "], [6, "Navoiy viloyati"]))
        assert totals(checked)["new"] == 1

    def test_wrong_file_type(self, staff):
        upload = SimpleUploadedFile("list.txt", b"Raqami,Nomi\n1,A\n")
        response = check(staff, "schools/region", upload)
        assert "Bu fayl turi qabul qilinmaydi" in response.content.decode()

    def test_data_changed_after_the_check_saves_nothing(self, staff, regions):
        upload = xlsx(["Raqami", "Nomi"], [5, "Buxoro viloyati"], [6, "Navoiy viloyati"])
        checked = check(staff, "schools/region", upload)
        # Meanwhile someone adds region 6 and gives the name "Navoiy viloyati" to another one.
        Region.objects.create(number=6, name="Navoiy")
        Region.objects.create(number=99, name="Navoiy viloyati")

        response = confirm(staff, "schools/region", checked)
        assert response.status_code == 302
        assert response["Location"].endswith("/admin/schools/region/import/")
        assert not Region.objects.filter(number=5).exists()  # the good row was rolled back too

    def test_sample_file(self, staff):
        response = staff.get("/admin/schools/school/import/template/")
        assert response.status_code == 200
        rows = read_xlsx(response.content)
        assert rows[0] == ["Viloyat", "Tuman", "Raqami", "Nomi", "Faol"]
        assert len(rows) == 3

    def test_pages_render(self, staff, regions):
        page = staff.get("/admin/schools/region/import/").content.decode()
        assert "Fayl qanday bo‘lishi kerak" in page and "majburiy" in page
        page = staff.get("/admin/schools/region/export/").content.decode()
        assert "2 ta yozuv yuklab olinadi" in page
        page = staff.get("/admin/schools/region/").content.decode()
        assert "Fayldan yuklash" in page and "Yuklab olish" in page


class TestDistrictsAndSchools:
    def test_region_by_name_with_another_apostrophe_or_by_number(self, staff, regions):
        upload = xlsx(
            ["Viloyat", "Raqami", "Nomi"],
            ["Farg'ona viloyati", 1, "Qo‘qon shahri"],
            [2, 1, "Andijon shahri"],
        )
        confirm(staff, "schools/district", check(staff, "schools/district", upload))
        assert District.objects.get(name="Qo‘qon shahri").region.number == 4
        assert District.objects.get(name="Andijon shahri").region.number == 2

    def test_unknown_region(self, staff, regions):
        upload = xlsx(["Viloyat", "Raqami", "Nomi"], ["Samarqand", 1, "Urgut tumani"])
        found = errors_of(check(staff, "schools/district", upload))
        assert (2, "Viloyat", "“Samarqand” degan viloyat topilmadi.") in found

    def test_school_is_found_in_the_district_of_its_own_region(self, staff, regions):
        andijon, fargona = regions
        in_andijon = District.objects.create(region=andijon, number=1, name="Markaziy tuman")
        in_fargona = District.objects.create(region=fargona, number=1, name="Markaziy tuman")
        School.objects.create(district=in_fargona, number=12, name="12-maktab")

        upload = xlsx(
            ["Viloyat", "Tuman", "Raqami", "Nomi"],
            ["Farg‘ona viloyati", "Markaziy tuman", 12, "12-maktab (yangi nomi)"],
            ["Andijon viloyati", "markaziy  tuman", 12, "12-maktab"],
        )
        checked = check(staff, "schools/school", upload)
        assert totals(checked) == {"new": 1, "update": 1, "skip": 0}
        confirm(staff, "schools/school", checked)
        assert School.objects.get(district=in_fargona).name == "12-maktab (yangi nomi)"
        assert School.objects.get(district=in_andijon).number == 12

    def test_school_without_number_is_found_by_name(self, staff, regions):
        district = District.objects.create(region=regions[0], number=1, name="Asaka tumani")
        school = School.objects.create(district=district, name="Prezident maktabi", status=False)
        upload = xlsx(
            ["Viloyat", "Tuman", "Raqami", "Nomi", "Faol"],
            [2, 1, None, "Prezident maktabi", None],
        )
        checked = check(staff, "schools/school", upload)
        assert totals(checked) == {"new": 0, "update": 0, "skip": 1}
        school.refresh_from_db()
        assert school.status is False  # an empty "Faol" keeps the current state

    def test_district_not_in_that_region(self, staff, regions):
        District.objects.create(region=regions[0], number=1, name="Asaka tumani")
        upload = xlsx(
            ["Viloyat", "Tuman", "Nomi"], ["Farg‘ona viloyati", "Asaka tumani", "1-maktab"]
        )
        found = errors_of(check(staff, "schools/school", upload))
        assert (2, "Tuman", "“Asaka tumani” degan tuman Farg‘ona viloyatida topilmadi.") in found

    def test_school_export_names_region_and_district(self, staff, regions):
        district = District.objects.create(region=regions[0], number=3, name="Asaka tumani")
        School.objects.create(district=district, number=5, name="5-maktab")
        rows = read_xlsx(export(staff, "/admin/schools/school/export/", "0").content)
        assert rows == [
            ["Viloyat", "Tuman", "Raqami", "Nomi", "Faol"],
            ["Andijon viloyati", "Asaka tumani", 5, "5-maktab", "ha"],
        ]


QUESTION_HEADERS = ["Raqami", "Fan", "Qiyinlik", "Savol matni", "A", "B", "C", "To‘g‘ri javob"]


class TestQuestions:
    @pytest.fixture
    def exam(self, db):
        return make_exam()

    def check_questions(self, client, exam, upload):
        return check(client, "exams/question", upload, exam=exam.pk)

    def test_plain_text_questions_are_added_to_the_chosen_exam(self, staff, exam):
        upload = xlsx(
            QUESTION_HEADERS,
            [7, "Matematika", "Qiyin", "Hisoblang: 2 + 3", 4, 5, 6, "b"],
            [8, "Mantiq", None, "<p>Qaysi biri <b>ortiqcha</b>?</p>", "Olma", "Nok", "Sabzi", "С"],
        )
        checked = self.check_questions(staff, exam, upload)
        assert totals(checked) == {"new": 2, "update": 0, "skip": 0}
        confirm(staff, "exams/question", checked)

        seventh = Question.objects.get(exam=exam, number=7)
        assert (seventh.subject, seventh.difficulty) == ("math", 3)
        assert seventh.prompt == "<p>Hisoblang: 2 + 3</p>"
        options = {o.label: (o.content, o.is_correct) for o in seventh.options.all()}
        assert options == {
            "A": ("<p>4</p>", False),
            "B": ("<p>5</p>", True),
            "C": ("<p>6</p>", False),
        }
        eighth = Question.objects.get(exam=exam, number=8)
        assert eighth.subject == "iq"  # by an alias
        assert eighth.options.get(is_correct=True).label == "C"  # typed with a Cyrillic С

    def test_update_keeps_option_ids_so_answers_stay_valid(self, staff, exam):
        question = Question.objects.get(exam=exam, number=1)
        ids = {o.label: o.pk for o in question.options.all()}
        upload = xlsx(
            ["Raqami", "A", "B", "To‘g‘ri javob"], [1, "yangi to‘g‘ri", "yangi noto‘g‘ri", "B"]
        )
        confirm(staff, "exams/question", self.check_questions(staff, exam, upload))
        options = {o.label: o for o in question.options.all()}
        assert {label: o.pk for label, o in options.items()} == ids
        assert options["B"].is_correct and not options["A"].is_correct
        assert options["A"].content == "<p>yangi to‘g‘ri</p>"

    def test_only_some_columns_change_only_those(self, staff, exam):
        upload = xlsx(["Raqami", "Izoh"], [2, "Yangi izoh"])
        checked = self.check_questions(staff, exam, upload)
        assert totals(checked)["update"] == 1
        confirm(staff, "exams/question", checked)
        question = Question.objects.get(exam=exam, number=2)
        assert question.explanation == "<p>Yangi izoh</p>"
        assert question.options.count() == 2  # no option columns: options untouched

    @pytest.mark.parametrize(
        ("row", "column", "message"),
        [
            ([9, "Matematika", None, "Savol", "Bir", None, None, "A"], "A", "Kamida ikkita"),
            ([9, "Matematika", None, "Savol", "Bir", None, "Uch", "A"], "A", "ketma-ket"),
            (
                [9, "Matematika", None, "Savol", "Bir", "Ikki", None, ""],
                "To‘g‘ri javob",
                "harfini yozing",
            ),
            (
                [9, "Matematika", None, "Savol", "Bir", "Ikki", None, "C"],
                "To‘g‘ri javob",
                "“C” varianti bo‘sh",
            ),
            (
                [9, "Kimyo", None, "Savol", "Bir", "Ikki", None, "A"],
                "Fan",
                "“Kimyo” degan qiymat yo‘q",
            ),
            (
                [9, "Matematika", "Juda qiyin", "Savol", "Bir", "Ikki", None, "A"],
                "Qiyinlik",
                "degan qiymat yo‘q",
            ),
            ([9, "Matematika", None, None, "Bir", "Ikki", None, "A"], "Savol matni", ""),
        ],
    )
    def test_row_problems(self, staff, exam, row, column, message):
        found = errors_of(self.check_questions(staff, exam, xlsx(QUESTION_HEADERS, row)))
        assert any(c == column and message in m for _, c, m in found), found
        assert not Question.objects.filter(exam=exam, number=9).exists()

    def test_subject_needs_a_section_in_the_exam(self, staff, exam):
        exam.sections.filter(subject="language").delete()
        upload = xlsx(QUESTION_HEADERS, [9, "Ona tili", None, "Savol", "Bir", "Ikki", None, "A"])
        found = errors_of(self.check_questions(staff, exam, upload))
        assert any(c == "Fan" and "bo‘limi yo‘q" in m for _, c, m in found)

    def test_options_of_an_exam_pupils_took_cannot_be_removed(self, staff, exam):
        pupil = make_pupil("11111111111111", "Aliya")
        start_attempt(pupil, exam.pk)
        upload = xlsx(["Raqami", "A", "B", "To‘g‘ri javob"], [1, "Faqat bitta", None, "A"])
        found = errors_of(self.check_questions(staff, exam, upload))
        assert any("o‘chirib bo‘lmaydi: B" in m for _, _, m in found), found

    def test_exam_must_be_chosen(self, staff, exam):
        response = check(staff, "exams/question", xlsx(QUESTION_HEADERS))
        assert response.context["form"].errors["exam"]

    def test_round_trip_through_excel(self, staff, exam):
        exported = export(staff, f"/admin/exams/question/export/?exam__id__exact={exam.pk}", "0")
        rows = read_xlsx(exported.content)
        assert rows[0][:5] == ["Imtihon", "Raqami", "Fan", "Qiyinlik", "Savol matni"]
        assert rows[0][-7:] == ["A", "B", "C", "D", "E", "F", "To‘g‘ri javob"]
        assert rows[1][:5] == ["Test imtihon", 1, "Matematika", None, text("Savol 1")]
        assert rows[1][-7:] == [text("to‘g‘ri"), text("noto‘g‘ri"), None, None, None, None, "A"]

        upload = SimpleUploadedFile("back.xlsx", exported.content)
        assert totals(self.check_questions(staff, exam, upload)) == {
            "new": 0,
            "update": 0,
            "skip": 6,
        }

    def test_question_with_a_picture_goes_out_as_json(self, staff, exam):
        picture = "data:image/webp;base64," + "A" * 40_000
        Question.objects.filter(exam=exam, number=1).update(
            prompt=f'<p>Rasm:</p><figure class="image"><img src="{picture}"></figure>'
        )
        url = f"/admin/exams/question/export/?exam__id__exact={exam.pk}"
        refused = export(staff, url, "0", follow=True)
        assert "JSON formatida yuklab oling" in refused.content.decode()

        exported = export(staff, url, "1")
        data = json.loads(exported.content)
        assert data[0]["Raqami"] == 1 and picture in data[0]["Savol matni"]
        upload = SimpleUploadedFile("back.json", exported.content, content_type="application/json")
        checked = self.check_questions(staff, exam, upload)
        assert totals(checked) == {"new": 0, "update": 0, "skip": 6}

    def test_check_page_shows_summaries_not_html(self, staff, exam):
        upload = xlsx(["Raqami", "Savol matni"], [1, "<p>Yangi <b>savol</b> matni</p>"])
        page = self.check_questions(staff, exam, upload).content.decode()
        assert "Yangi savol matni" in page
        assert "&lt;b&gt;" not in page

    def test_import_button_keeps_the_exam_filter(self, staff, exam):
        page = staff.get(f"/admin/exams/question/?exam__id__exact={exam.pk}").content.decode()
        assert f"/admin/exams/question/import/?exam={exam.pk}" in page
        form = staff.get(f"/admin/exams/question/import/?exam={exam.pk}").context["form"]
        assert str(form["exam"].value()) == str(exam.pk)

    def test_stray_option_letter_stops_the_export(self, staff, exam):
        AnswerOption.objects.filter(question__number=1, label="B").update(label="Z")
        response = export(staff, "/admin/exams/question/export/", "1", follow=True)
        assert "“Z” harfli variant bor" in response.content.decode()


class TestPermissions:
    def make_user(self, client, *codenames):
        name = "operator" + "-".join(codenames)
        user = get_user_model().objects.create_user(name, password="pass", is_staff=True)
        user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
        client.force_login(user)
        return client

    def test_view_permission_is_enough_to_export_but_not_to_import(self, client, regions):
        self.make_user(client, "view_region")
        assert export(client, "/admin/schools/region/export/", "0").status_code == 200
        assert client.get("/admin/schools/region/import/").status_code == 403
        assert client.get("/admin/schools/region/import/template/").status_code == 403
        assert "Fayldan yuklash" not in client.get("/admin/schools/region/").content.decode()

    def test_import_needs_both_add_and_change(self, client, regions):
        self.make_user(client, "view_region", "add_region")
        assert client.get("/admin/schools/region/import/").status_code == 403
        client.logout()
        self.make_user(client, "view_region", "add_region", "change_region")
        assert client.get("/admin/schools/region/import/").status_code == 200
