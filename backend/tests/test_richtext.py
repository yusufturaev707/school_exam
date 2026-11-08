"""Question text from the editor: cleaned on the way in, delivered intact, formulas untouched."""

import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from apps.core.richtext import is_blank_html, sanitize_html
from apps.exams.models import AnswerOption, Question

from .conftest import make_exam

FORMULA = r"$\frac{1}{2} + x^2 < 3 \cdot \sqrt{y}$"


class TestSanitize:
    @pytest.mark.parametrize(
        "dirty",
        [
            "<script>alert(1)</script>",
            '<img src="x" onerror="alert(1)">',
            '<p onclick="alert(1)">x</p>',
            '<iframe src="https://evil.example"></iframe>',
            '<a href="javascript:alert(1)">x</a>',
            '<img src="javascript:alert(1)">',
            '<img src="data:text/html;base64,PHNjcmlwdD4=">',
            "<style>body{display:none}</style>",
            '<p style="background:url(https://evil.example/x)">x</p>',
            '<form action="https://evil.example"><input name="jshshir"></form>',
            "<svg onload=alert(1)></svg>",
        ],
    )
    def test_dangerous_html_is_removed(self, dirty):
        cleaned = sanitize_html(dirty).lower()
        for fragment in ("script", "onerror", "onclick", "iframe", "javascript:", "evil.example",
                         "<style", "<form", "<input", "<svg", "text/html"):  # fmt: skip
            assert fragment not in cleaned

    def test_links_are_dropped_but_their_text_stays(self):
        assert sanitize_html('<p><a href="https://x.uz">matn</a></p>') == "<p>matn</p>"

    @pytest.mark.parametrize(
        "safe",
        [
            "<p><strong>Qalin</strong> <em>qiya</em> <u>chiziq</u> x<sub>1</sub> y<sup>2</sup></p>",
            "<ul><li>bir</li></ul><ol><li>ikki</li></ol>",
            "<table><tbody><tr><td>1</td><td>2</td></tr></tbody></table>",
            '<figure><img src="/media/rasm.png" alt="Rasm"></figure>',
            '<img src="https://cdn.uz/rasm.png" alt="">',
            '<img src="data:image/svg+xml;charset=utf-8,%3Csvg%3E" alt="">',
            '<p style="text-align:center">x</p>',
        ],
    )
    def test_editor_formatting_is_kept(self, safe):
        assert sanitize_html(safe) == safe

    @pytest.mark.parametrize(
        "formula",
        [
            r"$\frac{1}{2}$",
            r"$$\sum_{i=1}^{n} i^2$$",
            r"\(a_1 + b_2\)",
            r"\[\sqrt{x}\]",
            r"$\begin{matrix} 1 &amp; 2 \end{matrix}$",
            r"$a &lt; b$",
        ],
    )
    def test_formulas_survive_unchanged(self, formula):
        html = f"<p>Hisoblang: {formula}</p>"
        assert sanitize_html(html) == html

    def test_cleaning_twice_changes_nothing(self):
        once = sanitize_html(f"<p>{FORMULA}</p><script>x</script>")
        assert sanitize_html(once) == once

    @pytest.mark.parametrize("empty", ["", "<p></p>", "<p>&nbsp;</p>", "<p> </p><p><br></p>"])
    def test_empty_editor_output_counts_as_blank(self, empty):
        assert is_blank_html(empty)

    @pytest.mark.parametrize("filled", ["<p>x</p>", '<img src="/media/a.png">', "<p>$x$</p>"])
    def test_real_content_is_not_blank(self, filled):
        assert not is_blank_html(filled)


@pytest.mark.django_db
class TestStorage:
    def test_every_save_path_cleans(self, exam):
        question = exam.questions.first()
        question.prompt = "<p>Savol</p><script>alert(1)</script>"
        question.save()
        question.refresh_from_db()
        assert question.prompt == "<p>Savol</p>"

        option = AnswerOption.objects.create(
            question=question, label="Z", content='<p onclick="x()">Javob</p>'
        )
        option.refresh_from_db()
        assert option.content == "<p>Javob</p>"


@pytest.mark.django_db
class TestApi:
    def payload(self, api, exam):
        attempt_id = api.post(f"/api/examinations/{exam.pk}/start").json()["attemptId"]
        return api.get(f"/api/examinations/attempts/{attempt_id}").json()

    def test_question_is_delivered_as_html_blocks_with_formula_intact(self, api, exam):
        Question.objects.filter(exam=exam, number=1).delete()
        Question.objects.create(
            exam=exam, number=1, subject="math", prompt=f"<p>{FORMULA.replace('<', '&lt;')}</p>"
        )
        first = self.payload(api, exam)["questions"][0]
        assert first["prompt"] == [
            {"type": "html", "html": r"<p>$\frac{1}{2} + x^2 &lt; 3 \cdot \sqrt{y}$</p>"}
        ]

    def test_empty_optional_texts_are_null(self, api, exam):
        first = self.payload(api, exam)["questions"][0]
        assert first["passage"] is None

    def test_passage_is_sent_when_present(self, api, exam):
        question = exam.questions.first()
        question.passage = "<p>Uzun matn</p>"
        question.save()
        first = self.payload(api, exam)["questions"][0]
        assert first["passage"] == [{"type": "html", "html": "<p>Uzun matn</p>"}]

    def test_options_never_reveal_the_answer(self, api, exam):
        first = self.payload(api, exam)["questions"][0]
        assert set(first["options"][0]) == {"id", "label", "content"}


@pytest.mark.django_db
class TestAdmin:
    @pytest.fixture
    def staff(self, client):
        client.force_login(get_user_model().objects.create_superuser("admin", password="x"))
        return client

    def test_question_form_uses_the_editor(self, staff):
        page = staff.get("/admin/exams/question/add/").content.decode()
        assert "django_ckeditor_5" in page
        assert page.count('class="django_ckeditor_5') >= 3

    def test_preview_shows_saved_question_with_the_formula(self, staff):
        question = make_exam().questions.first()
        question.prompt = f"<p>{FORMULA.replace('<', '&lt;')}</p>"
        question.save()
        page = staff.get(f"/admin/exams/question/{question.pk}/change/").content.decode()
        assert 'class="question-preview"' in page
        assert r"<p>$\frac{1}{2} + x^2 &lt; 3 \cdot \sqrt{y}$</p>" in page
        assert "exams/katex/auto-render.min.js" in page

    def test_preview_of_a_new_question_is_a_hint(self, staff):
        assert "Saqlangandan keyin" in staff.get("/admin/exams/question/add/").content.decode()


def png_file(name="rasm.png") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.mark.django_db
class TestImageUpload:
    URL = "/ckeditor5/image_upload/"

    @pytest.fixture(autouse=True)
    def temporary_media(self, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        settings.MEDIA_URL = "/media/"

    @pytest.fixture
    def staff(self):
        client = Client()
        client.force_login(get_user_model().objects.create_superuser("admin", password="x"))
        return client

    def test_staff_can_upload_an_image(self, staff, tmp_path):
        response = staff.post(self.URL, {"upload": png_file()})
        assert response.status_code == 200, response.content
        assert response.json()["url"].startswith("/media/")
        assert list(tmp_path.iterdir())

    def test_anonymous_can_not_upload(self):
        assert Client().post(self.URL, {"upload": png_file()}).status_code == 403

    def test_a_logged_in_pupil_can_not_upload(self, aliya):
        from .conftest import client_for

        client = client_for(aliya)
        assert client.post(self.URL, {"upload": png_file()}, format="multipart").status_code == 403

    @pytest.mark.parametrize(
        "name,body",
        [
            ("x.svg", b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>'),
            ("x.html", b"<script>alert(1)</script>"),
            ("x.png", b"not really an image"),
        ],
    )
    def test_only_real_images_are_accepted(self, staff, tmp_path, name, body):
        upload = SimpleUploadedFile(name, body)
        assert staff.post(self.URL, {"upload": upload}).status_code == 400
        assert not list(tmp_path.iterdir())
