"""The results report in the admin: its numbers, its filters and its four files."""

import json
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from openpyxl import load_workbook
from PIL import Image

from apps.exams.models import Question
from apps.exams.services import save_answer, start_attempt, submit_attempt

from .conftest import ALIYA_JSHSHIR, BEK_JSHSHIR, make_classroom, make_exam, make_pupil, options_of

pytestmark = pytest.mark.django_db

REPORT = reverse("admin:exams_examresult_report")


def download(file_format: str) -> str:
    return reverse("admin:exams_examresult_report_download", args=[file_format])


@pytest.fixture
def staff(client):
    user = get_user_model().objects.create_superuser("admin", password="pass-for-tests")
    client.force_login(user)
    return client


def take(pupil, exam, right: int) -> None:
    """The pupil answers the first `right` questions correctly and the next one wrongly."""
    attempt, _ = start_attempt(pupil, exam.pk)
    questions = list(Question.objects.filter(exam=exam).order_by("number"))
    for index, question in enumerate(questions[: right + 1]):
        good, bad = options_of(question)
        save_answer(pupil, attempt.pk, question.pk, [good if index < right else bad], index + 1)
    submit_attempt(pupil, attempt.pk, "manual", [])


@pytest.fixture
def results():
    exam = make_exam()
    aliya = make_pupil(ALIYA_JSHSHIR, "Aliya")  # 6 of 6
    bek = make_pupil(BEK_JSHSHIR, "Bek")  # 3 of 6, one wrong, two unanswered
    other = make_pupil("33333333333333", "Vali")
    other.classroom = make_classroom(school_number=2)
    other.save()  # 0 of 6, in another school
    take(aliya, exam, 6)
    take(bek, exam, 3)
    take(other, exam, 0)
    return exam


def report_of(staff, exam, **params):
    response = staff.get(REPORT, {"attempt__exam__id__exact": exam.pk, **params})
    assert response.status_code == 200
    return response.context["report"]


def test_numbers(staff, results):
    report = report_of(staff, results)
    summary = report["summary"]
    assert summary["count"] == 3
    assert summary["averagePercent"] == 50.0
    assert summary["maxPercent"] == 100.0
    assert summary["minPercent"] == 0.0
    assert [p["name"] for p in report["pupils"]] == ["Test Aliya", "Test Bek", "Test Vali"]
    assert [p["rank"] for p in report["pupils"]] == [1, 2, 3]
    assert [b["count"] for b in report["bands"]] == [1, 1, 1]
    assert report["distribution"][9]["count"] == 1 and report["distribution"][5]["count"] == 1
    first = report["questions"][0]  # everyone answered it: 2 right, Vali wrong
    assert (first["correct"], first["incorrect"], first["unanswered"]) == (2, 1, 0)
    sixth = report["questions"][5]  # only Aliya got there
    assert (sixth["correct"], sixth["incorrect"], sixth["unanswered"]) == (1, 0, 2)


def test_equal_scores_share_a_place(staff, results):
    pupil = make_pupil("44444444444444", "Gulnora")
    take(pupil, results, 3)
    assert [p["rank"] for p in report_of(staff, results)["pupils"]] == [1, 2, 2, 4]


def test_groups_go_one_level_below_the_chosen_place(staff, results):
    report = report_of(staff, results)
    assert report["groups"]["param"] == "region"
    school = make_classroom(school_number=2).school
    report = report_of(
        staff, results, region=school.district.region_id, district=school.district_id
    )
    assert report["groups"]["param"] == "school"
    assert [(g["name"], g["count"]) for g in report["groups"]["rows"]] == [
        ("1-maktab", 2),
        ("2-maktab", 1),
    ]


def test_place_filter_narrows_the_report(staff, results):
    school = make_classroom(school_number=2).school
    report = report_of(
        staff,
        results,
        region=school.district.region_id,
        district=school.district_id,
        school=school.pk,
    )
    assert [p["name"] for p in report["pupils"]] == ["Test Vali"]
    assert {"label": "Maktab", "value": "2-maktab"} in report["filters"]


def test_without_an_exam_one_exam_is_taken_and_several_are_offered(staff, results):
    assert staff.get(REPORT).context["report"]["summary"]["count"] == 3
    second = make_exam(title="Ikkinchi")
    take(make_pupil("55555555555555", "Diyor"), second, 1)
    response = staff.get(REPORT)
    assert response.context["report"] is None
    assert {item["title"] for item in response.context["exam_choices"]} == {
        "Test imtihon",
        "Ikkinchi",
    }


@pytest.mark.parametrize("file_format", ["json", "xlsx", "pdf", "png"])
def test_files(staff, results, file_format):
    response = staff.get(download(file_format), {"attempt__exam__id__exact": results.pk})
    assert response.status_code == 200
    assert f'.{file_format}"' in response["Content-Disposition"]
    body = response.content
    if file_format == "json":
        assert json.loads(body)["summary"]["count"] == 3
    elif file_format == "xlsx":
        book = load_workbook(BytesIO(body))
        assert book.sheetnames == ["Umumiy", "O‘quvchilar", "Fanlar", "Viloyatlar", "Savollar"]
        sheet = book["O‘quvchilar"]
        assert sheet["B2"].value == "Test Aliya" and sheet.max_row == 4
    elif file_format == "pdf":
        assert body.startswith(b"%PDF")
    else:
        assert Image.open(BytesIO(body)).format == "PNG"


def test_files_of_an_empty_selection(staff, results):
    for file_format in ["json", "xlsx", "pdf", "png"]:
        response = staff.get(
            download(file_format), {"attempt__exam__id__exact": results.pk, "q": "yo'q"}
        )
        assert response.status_code == 200, file_format


def test_names_that_look_like_formulas_stay_text_in_excel(staff, results):
    pupil = make_pupil("66666666666666", "Gul")
    pupil.last_name = "=HYPERLINK(1)"
    pupil.save()
    take(pupil, results, 1)
    body = staff.get(download("xlsx"), {"attempt__exam__id__exact": results.pk}).content
    cells = [row[1] for row in load_workbook(BytesIO(body))["O‘quvchilar"].iter_rows(min_row=2)]
    cell = next(cell for cell in cells if "HYPERLINK" in str(cell.value))
    assert cell.value == "=HYPERLINK(1) Gul" and cell.data_type == "s"


def test_unknown_format_and_bad_filter(staff, results):
    assert staff.get(download("exe"), {"attempt__exam__id__exact": results.pk}).status_code == 404
    assert staff.get(REPORT, {"nonsense": "1"}).status_code == 404


def test_needs_view_permission(client, results):
    user = get_user_model().objects.create_user("teacher", password="pass", is_staff=True)
    client.force_login(user)
    assert client.get(REPORT).status_code == 403
    assert client.get(download("json")).status_code == 403


def test_buttons_lead_to_the_report(staff, results):
    page = staff.get(reverse("admin:exams_examresult_changelist")).content.decode()
    assert REPORT in page
    page = staff.get(reverse("admin:exams_exam_change", args=[results.pk])).content.decode()
    assert f"{REPORT}?attempt__exam__id__exact={results.pk}" in page
