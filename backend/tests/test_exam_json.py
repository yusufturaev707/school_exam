"""A whole exam as one JSON file in the admin, and JSON files for the place lists."""

import io
import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command

from apps.exams.importer import export_exam_data, import_exam_data
from apps.exams.models import AnswerOption, AttemptAnswer, Exam, ExamTarget
from apps.exams.services import start_attempt
from apps.schools.models import Region

from .conftest import ALIYA_JSHSHIR, make_pupil, make_region

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


class TestCommands:
    """`export_exams` here, `import_exam` on the server: the questions move in one file."""

    def test_export_then_import_on_another_server(self, tmp_path):
        first = import_exam_data(diagnostic(), publish=True)
        second = import_exam_data({**diagnostic(), "title": "Ikkinchi imtihon", "grades": []})
        path = tmp_path / "imtihonlar.json"
        call_command("export_exams", "--out", str(path))
        exported = json.loads(path.read_text(encoding="utf-8"))
        assert [exam["title"] for exam in exported] == [first.title, second.title]

        Exam.objects.all().delete()  # "another server"
        out = io.StringIO()
        call_command("import_exam", str(path), "--publish", stdout=out)
        assert Exam.objects.count() == 2
        assert all(exam.is_published for exam in Exam.objects.all())
        assert [export_exam_data(e) for e in Exam.objects.order_by("created_at")] == exported
        assert "with 30 questions (published)" in out.getvalue()

    def test_running_twice_makes_no_copies(self, tmp_path):
        path = tmp_path / "imtihonlar.json"
        path.write_text(json.dumps([diagnostic()]), encoding="utf-8")
        call_command("import_exam", str(path))
        out = io.StringIO()
        call_command("import_exam", str(path), stdout=out)
        assert Exam.objects.count() == 1
        assert "Skipped" in out.getvalue()
        call_command("import_exam", str(path), "--force", stdout=io.StringIO())
        assert Exam.objects.count() == 2

    def test_one_broken_exam_saves_none_of_the_file(self, tmp_path):
        broken = {**diagnostic(), "title": "Buzuq"}
        broken["questions"][0]["options"][0]["isCorrect"] = True  # B is already correct
        path = tmp_path / "imtihonlar.json"
        path.write_text(json.dumps([diagnostic(), broken]), encoding="utf-8")
        with pytest.raises(CommandError, match="“Buzuq” imtihoni: 1-savol"):
            call_command("import_exam", str(path))
        assert not Exam.objects.exists()

    def test_export_of_one_title(self, tmp_path):
        import_exam_data(diagnostic())
        with pytest.raises(CommandError, match="No exam with title"):
            call_command("export_exams", "--out", str(tmp_path / "x.json"), "--title", "Yo‘q")


def test_admin_takes_a_file_with_several_exams(staff):
    data = [diagnostic(), {**diagnostic(), "title": "Ikkinchi"}]
    response = staff.post(IMPORT_URL, {"file": json_file(data)})
    assert response["Location"] == "/admin/exams/exam/"
    assert Exam.objects.count() == 2


READY = Path(__file__).resolve().parent.parent / "content" / "imtihonlar.json"


class TestUpdateInPlace:
    """The server has an older copy of the exam: `import_exam --update` brings it in line."""

    def run(self, path, *flags) -> str:
        out = io.StringIO()
        call_command("import_exam", str(path), "--update", *flags, stdout=out)
        return out.getvalue()

    def test_older_copy_on_the_server_is_updated_not_duplicated(self):
        old = import_exam_data(diagnostic())  # the version from content/diagnostika-4-sinf.json
        ids = dict(old.questions.values_list("number", "id"))
        option_ids = set(
            AnswerOption.objects.filter(question__exam=old).values_list("id", flat=True)
        )

        output = self.run(READY, "--publish")

        assert Exam.objects.filter(title=old.title).count() == 1
        old.refresh_from_db()
        assert old.is_published
        assert dict(old.questions.values_list("number", "id")) == ids
        assert (
            set(AnswerOption.objects.filter(question__exam=old).values_list("id", flat=True))
            == option_ids
        )
        ready = json.loads(READY.read_text(encoding="utf-8"))[0]
        assert export_exam_data(old) == ready
        assert "questions changed" in output and "0 added, 0 removed" in output

        assert "0 questions changed" in self.run(READY)  # once more: nothing left to change

    def test_published_state_is_kept_without_publish(self):
        exam = import_exam_data(diagnostic(), publish=True)
        self.run(READY)
        exam.refresh_from_db()
        assert exam.is_published

    def test_pupils_answers_survive_and_their_exam_cannot_lose_questions(self, tmp_path):
        exam = import_exam_data(diagnostic(), publish=True)
        ExamTarget.objects.create(exam=exam, region=make_region())  # the test pupil is in 5th grade
        pupil = make_pupil(ALIYA_JSHSHIR, "Aliya")
        attempt, _ = start_attempt(pupil, exam.pk)
        option = AnswerOption.objects.get(question__exam=exam, question__number=1, label="B")
        AttemptAnswer.objects.create(
            attempt=attempt,
            question=option.question,
            selected_option_ids=[str(option.pk)],
            client_seq=1,
        )

        self.run(READY)  # changes texts only: fine
        option.refresh_from_db()
        assert option.is_correct

        shorter = json.loads(READY.read_text(encoding="utf-8"))
        shorter[0]["questions"].pop()
        path = tmp_path / "shorter.json"
        path.write_text(json.dumps(shorter), encoding="utf-8")
        before = export_exam_data(exam)
        with pytest.raises(CommandError, match="o‘chirib bo‘lmaydi: 30"):
            self.run(path)
        assert export_exam_data(exam) == before

    def test_without_pupils_missing_questions_and_options_are_removed(self, tmp_path):
        exam = import_exam_data(diagnostic())
        data = diagnostic()
        data["questions"].pop()
        data["questions"][0]["options"].pop()  # D
        path = tmp_path / "shorter.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        assert "1 removed" in self.run(path)
        assert exam.questions.count() == 29
        assert exam.questions.get(number=1).options.count() == 3

    def test_new_questions_are_added(self, tmp_path):
        exam = import_exam_data(diagnostic())
        data = diagnostic()
        extra = {**data["questions"][0], "number": 31}
        data["questions"].append(extra)
        path = tmp_path / "longer.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        assert "1 added" in self.run(path)
        assert exam.questions.count() == 31

    def test_two_exams_with_the_title_are_not_guessed_between(self):
        import_exam_data(diagnostic())
        import_exam_data(diagnostic())
        with pytest.raises(CommandError, match="2 ta imtihon bor"):
            self.run(READY)


ENGLISH = Path(__file__).resolve().parent.parent / "content" / "ingliz-tili-4-sinf.json"


class TestEnglishTest:
    """content/ingliz-tili-4-sinf.json, made by content/ingliz_tili_4_sinf.py from its source."""

    def test_file_matches_its_source(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "ingliz_tili_4_sinf", ENGLISH.with_name("ingliz_tili_4_sinf.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.build() == json.loads(ENGLISH.read_text(encoding="utf-8"))

    def test_answers_match_the_source(self):
        source = json.loads(
            (ENGLISH.parent / "sources" / "ingliz_tili_4_sinf_turli_testlar_v2.json").read_text(
                encoding="utf-8"
            )
        )
        exam = json.loads(ENGLISH.read_text(encoding="utf-8"))
        for item, question in zip(source, exam["questions"], strict=True):
            correct = next(o for o in question["options"] if o["isCorrect"])
            assert item["answer"].startswith(f"{correct['label']})")
            assert question["subject"] == "language"

    def test_it_loads_with_the_diagnostic_test_in_one_command(self):
        out = io.StringIO()
        call_command("import_exam", str(READY), "--update", "--publish", stdout=out)
        english = Exam.objects.get(title="4-sinf bitiruvchilari uchun ingliz tili testi")
        assert english.questions.count() == 30
        assert english.is_published
        assert list(english.sections.values_list("subject", "title")) == [
            ("language", "Ingliz tili")
        ]
        assert Exam.objects.count() == 2
