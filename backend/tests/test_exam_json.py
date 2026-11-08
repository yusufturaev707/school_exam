"""A whole exam as one JSON file in the admin, and JSON files for the place lists."""

import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.exams.importer import export_exam_data, import_exam_data
from apps.exams.models import Exam, ExamTarget
from apps.schools.models import Region

from .conftest import make_region

pytestmark = pytest.mark.django_db

CONTENT = Path(__file__).resolve().parent.parent / "content" / "diagnostika-4-sinf.json"
IMPORT_URL = "/admin/exams/exam/import-json/"


@pytest.fixture
def staff(client):
    user = get_user_model().objects.create_superuser("admin", password="pass-for-tests")
    client.force_login(user)
    return client


def json_file(data, name="exam.json") -> SimpleUploadedFile:
    raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
    return SimpleUploadedFile(name, raw, content_type="application/json")


def diagnostic() -> dict:
    return json.loads(CONTENT.read_text(encoding="utf-8"))


def errors(response) -> list[str]:
    return response.context["form"].errors["file"]


class TestExamImport:
    def test_file_becomes_an_unpublished_exam(self, staff):
        response = staff.post(IMPORT_URL, {"file": json_file(diagnostic())})
        exam = Exam.objects.get()
        assert response.status_code == 302
        assert response["Location"] == f"/admin/exams/exam/{exam.pk}/change/"
        assert exam.is_published is False
        assert exam.questions.count() == 30
        assert list(exam.targets.values_list("grade", flat=True)) == [4]

    def test_publish_at_once(self, staff):
        staff.post(IMPORT_URL, {"file": json_file(diagnostic()), "publish": "on"})
        assert Exam.objects.get().is_published

    def test_warns_when_nobody_is_assigned(self, staff):
        data = diagnostic()
        del data["grades"]
        page = staff.post(IMPORT_URL, {"file": json_file(data)}, follow=True).content.decode()
        assert "hech kimga biriktirilmagan" in page

    @pytest.mark.parametrize(
        ("broken", "message"),
        [
            (
                lambda d: d["questions"][4]["options"][0].update(isCorrect=True),
                "5-savol: aynan bitta",
            ),
            (lambda d: d["questions"][2].pop("prompt"), "3-savol: “prompt” maydoni yo‘q."),
            (lambda d: d["questions"][1].update(subject="kimyo"), "2-savol: Fan:"),
            (lambda d: d.update(durationMinutes=0), "Imtihon: Davomiyligi (daqiqa):"),
            (lambda d: d.pop("sections"), "Imtihon: “sections” maydoni yo‘q."),
            (lambda d: d.update(questions={}), "“questions” ro‘yxat"),
            (lambda d: d["questions"][3].update(number=1), "4-o‘rindagi savol (raqami 1):"),
        ],
    )
    def test_broken_file_saves_nothing_and_says_where(self, staff, broken, message):
        data = diagnostic()
        broken(data)
        response = staff.post(IMPORT_URL, {"file": json_file(data)})
        assert any(message in error for error in errors(response)), errors(response)
        assert not Exam.objects.exists()

    @pytest.mark.parametrize("raw", [b"not json", b"\xff\xfe broken", b"[1, 2]"])
    def test_not_an_exam_file(self, staff, raw):
        response = staff.post(IMPORT_URL, {"file": json_file(raw)})
        assert errors(response)
        assert not Exam.objects.exists()

    def test_page_and_button(self, staff):
        assert "JSON fayldan yuklash" in staff.get("/admin/exams/exam/").content.decode()
        assert "Darhol e’lon qilish" in staff.get(IMPORT_URL).content.decode()


class TestExamExport:
    def test_download_and_load_again_gives_the_same_exam(self, staff):
        exam = import_exam_data(diagnostic())
        ExamTarget.objects.create(exam=exam, region=make_region())  # a place: not in the file

        page = staff.get(f"/admin/exams/exam/{exam.pk}/change/").content.decode()
        assert f"/admin/exams/exam/{exam.pk}/export-json/" in page
        response = staff.get(f"/admin/exams/exam/{exam.pk}/export-json/")
        assert response["Content-Disposition"].endswith('.json"')
        exported = json.loads(response.content)
        assert exported["grades"] == [4]
        assert len(exported["questions"]) == 30

        staff.post(IMPORT_URL, {"file": json_file(response.content)})
        copy = Exam.objects.exclude(pk=exam.pk).get()
        assert export_exam_data(copy) == exported

    def test_view_permission_exports_but_cannot_import(self, client):
        exam = import_exam_data(diagnostic())
        user = get_user_model().objects.create_user("viewer", password="x", is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename="view_exam"))
        client.force_login(user)
        assert client.get(f"/admin/exams/exam/{exam.pk}/export-json/").status_code == 200
        assert client.get(IMPORT_URL).status_code == 403


def test_place_lists_take_json_too(staff):
    upload = json_file([{"Raqami": 3, "Nomi": "Namangan viloyati", "Faol": True}], "v.json")
    checked = staff.post("/admin/schools/region/import/", {"import_file": upload, "resource": "0"})
    assert checked.context["result"].totals["new"] == 1
    form = checked.context["confirm_form"]
    staff.post("/admin/schools/region/process_import/", {**form.initial})
    assert Region.objects.get(number=3).name == "Namangan viloyati"
