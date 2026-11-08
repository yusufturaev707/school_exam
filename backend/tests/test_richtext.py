"""Question text from the editor: cleaned on the way in, delivered intact, formulas untouched."""

import base64
import io
import re

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from apps.core.images import MAX_IMAGE_BYTES, MAX_SIDE, compress_image, data_uri
from apps.core.richtext import is_blank_html, sanitize_html
from apps.exams.models import AnswerOption, Question

from .conftest import make_exam

FORMULA = r"$\frac{1}{2} + x^2 < 3 \cdot \sqrt{y}$"
SVG = "data:image/svg+xml;charset=utf-8,%3Csvg%3E"


def image_bytes(size=(4, 4), fmt="PNG", colour="white", mode="RGB", **save) -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, size, colour).save(buffer, format=fmt, **save)
    return buffer.getvalue()


def as_uri(raw: bytes, mime="image/png") -> str:
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def decoded(src: str) -> Image.Image:
    assert src.startswith("data:image/webp;base64,"), src[:40]
    return Image.open(io.BytesIO(base64.b64decode(src.split(",", 1)[1])))


def only_src(html: str) -> str:
    return html.split('src="', 1)[1].split('"', 1)[0]


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
            f'<figure><img src="{SVG}" alt="Rasm"></figure>',
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

    @pytest.mark.parametrize("filled", ["<p>x</p>", f'<img src="{SVG}">', "<p>$x$</p>"])
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

    def test_periodic_resync_can_leave_the_heavy_questions_out(self, api, exam):
        attempt_id = api.post(f"/api/examinations/{exam.pk}/start").json()["attemptId"]
        full = api.get(f"/api/examinations/attempts/{attempt_id}").json()
        light = api.get(f"/api/examinations/attempts/{attempt_id}?questions=0").json()
        assert full["questions"] and "questions" not in light
        assert {key: full[key] for key in light if key != "serverTime"} == {
            key: value for key, value in light.items() if key != "serverTime"
        }
        assert set(full) - set(light) == {"questions"}

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

    def test_only_the_question_text_gets_the_full_toolbar(self, staff):
        page = staff.get("/admin/exams/question/add/").content.decode()
        configs = dict(
            re.findall(r'<span id="id_([\w-]+?)_script-span"[^>]*>(.*?)</span>', page, re.S)
        )
        assert "fontColor" in configs["prompt"]
        for name in ("passage", "explanation", "options-__prefix__-content"):
            assert "fontColor" not in configs[name]

    def test_preview_marks_the_right_answer(self, staff):
        question = make_exam().questions.first()
        page = staff.get(f"/admin/exams/question/{question.pk}/change/").content.decode()
        assert 'class="is-correct"' in page
        assert "question-preview__options" in page


class TestEditorFormatting:
    """What the extended toolbar produces survives cleaning; look-alikes from elsewhere don't."""

    @pytest.mark.parametrize(
        "html",
        [
            '<p><span style="color:#e0453a">qizil</span></p>',
            '<p><mark class="marker-yellow">muhim</mark></p>',
            '<p style="text-align:center">markazda</p>',
            '<p style="margin-left:40px">surilgan</p>',
            '<ol style="list-style-type:lower-latin" start="3"><li>c</li></ol>',
            f'<figure class="image image_resized" style="width:50%"><img src="{SVG}"></figure>',
            '<figure class="table"><table><tbody><tr><td>1</td></tr></tbody></table></figure>',
            "<p>a</p><hr><p>b</p>",
            "<p><s>chizilgan</s></p>",
        ],
    )
    def test_editor_output_is_kept(self, html):
        assert sanitize_html(html) == html

    @pytest.mark.parametrize(
        "dirty,clean",
        [
            ('<p><span style="color:#000000">x</span></p>', "<p><span>x</span></p>"),
            ('<p style="color:red;text-align:right">x</p>', '<p style="text-align:right">x</p>'),
            ('<p><mark class="marker-pink evil">x</mark></p>', "<p><mark>x</mark></p>"),
            ('<p style="margin-left:9000px">x</p>', "<p>x</p>"),
            ('<ol style="list-style-type:url(x)"><li>x</li></ol>', "<ol><li>x</li></ol>"),
            ('<figure class="image evil"><img src="' + SVG + '"></figure>',
             '<figure class="image"><img src="' + SVG + '"></figure>'),
        ],
    )  # fmt: skip
    def test_anything_else_is_dropped(self, dirty, clean):
        assert sanitize_html(dirty) == clean


def test_both_editor_configs_keep_html_output():
    """Markdown and FullPage each replace the output format: they must be removed together."""
    from django.conf import settings

    for config in settings.CKEDITOR_5_CONFIGS.values():
        removed = set(config["removePlugins"])
        assert {"Markdown", "FullPage", "Link", "LinkImage"} <= removed


class TestInlineImages:
    """Pictures are stored inside the HTML, compressed, and refused loudly when they can't be."""

    def test_a_pasted_png_becomes_a_small_webp(self):
        src = as_uri(image_bytes((50, 40)))
        html = sanitize_html(f'<p>Rasm:</p><img src="{src}" alt="Uchburchak">')
        image = decoded(only_src(html))
        assert image.format == "WEBP"
        assert image.size == (50, 40)
        assert html.startswith("<p>Rasm:</p><img") and 'alt="Uchburchak"' in html

    def test_a_large_photo_is_scaled_down(self):
        photo = image_bytes((4000, 3000), fmt="JPEG", colour="skyblue")
        assert decoded(data_uri(compress_image(photo))).size == (MAX_SIDE, 1200)

    def test_metadata_such_as_gps_is_removed_and_orientation_applied(self):
        exif = Image.Exif()
        exif[0x0112] = 6  # "rotate 90°": the phone was held upright
        exif[0x010F] = "Phone maker"
        photo = image_bytes((60, 30), fmt="JPEG", exif=exif.tobytes())
        image = decoded(data_uri(compress_image(photo)))
        assert image.size == (30, 60)
        assert not {"exif", "xmp", "icc_profile"} & image.info.keys()

    def test_transparency_is_kept(self):
        logo = image_bytes((20, 20), mode="RGBA", colour=(255, 0, 0, 0))
        assert decoded(data_uri(compress_image(logo))).mode == "RGBA"

    def test_saving_again_keeps_the_image_byte_for_byte(self):
        once = sanitize_html(f'<img src="{as_uri(image_bytes((300, 200), fmt="JPEG"))}">')
        assert sanitize_html(once) == once

    def test_an_svg_is_kept_as_written(self):
        assert sanitize_html(f'<img src="{SVG}">') == f'<img src="{SVG}">'

    @pytest.mark.parametrize(
        "src,reason",
        [
            ("https://cdn.uz/rasm.png", "boshqa saytdan"),
            ("/media/rasm.png", "boshqa saytdan"),
            ("file:///C:/Users/admin/rasm.png", "kompyuterdagi faylga"),
            ("blob:http://localhost/1", "kompyuterdagi faylga"),
            ("data:image/png;base64,@@@", "buzilgan"),
            ("data:image/png;base64," + base64.b64encode(b"not a picture").decode(), "rasm emas"),
            ("data:image/bmp;base64," + base64.b64encode(image_bytes(fmt="BMP")).decode(), "Faqat"),
        ],
    )
    def test_an_image_that_can_not_be_kept_is_reported(self, src, reason):
        problems = []
        html = sanitize_html(f'<p>Savol</p><img src="{src}">', problems)
        assert html == "<p>Savol</p>"
        assert len(problems) == 1 and reason in problems[0]

    def test_a_decompression_bomb_is_refused_before_decoding(self):
        bomb = image_bytes((7000, 7000), colour="black")  # ~49 megapixels in a few KB
        problems = []
        sanitize_html(f'<img src="{as_uri(bomb)}">', problems)
        assert "megapiksel" in problems[0]

    def test_a_noisy_photo_still_fits_the_budget(self):
        noise = Image.effect_noise((2400, 2400), 120).convert("RGB")
        buffer = io.BytesIO()
        noise.save(buffer, format="JPEG", quality=95)
        assert len(compress_image(buffer.getvalue())) <= MAX_IMAGE_BYTES


@pytest.mark.django_db
class TestInlineImageStorage:
    def test_saved_question_holds_the_compressed_picture(self, exam):
        question = exam.questions.first()
        question.prompt = f'<p>Savol</p><img src="{as_uri(image_bytes((80, 80)))}">'
        question.save()
        question.refresh_from_db()
        assert decoded(only_src(question.prompt)).format == "WEBP"

    def test_a_linked_picture_stops_the_save_with_a_reason(self, exam):
        question = exam.questions.first()
        question.prompt = '<p>Savol</p><img src="https://cdn.uz/rasm.png">'
        with pytest.raises(ValidationError, match="boshqa saytdan"):
            question.full_clean()

    def test_admin_form_shows_the_reason(self, exam, client):
        client.force_login(get_user_model().objects.create_superuser("admin", password="x"))
        question = exam.questions.first()
        data = {
            "exam": exam.pk, "number": question.number, "subject": question.subject,
            "type": question.type, "prompt": '<p>Savol</p><img src="file:///C:/a.png">',
            "passage": "", "explanation": "",
            "options-TOTAL_FORMS": 0, "options-INITIAL_FORMS": 0,
        }  # fmt: skip
        page = client.post(f"/admin/exams/question/{question.pk}/change/", data).content.decode()
        assert "kompyuterdagi faylga" in page


def png_file(name="rasm.png", size=(4, 4)) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, image_bytes(size), content_type="image/png")


@pytest.mark.django_db
class TestImageUpload:
    """The editor's upload button: the answer is the picture itself, nothing is written to disk."""

    URL = "/ckeditor5/image_upload/"

    @pytest.fixture
    def staff(self):
        client = Client()
        client.force_login(get_user_model().objects.create_superuser("admin", password="x"))
        return client

    def test_staff_get_the_compressed_picture_back(self, staff, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        response = staff.post(self.URL, {"upload": png_file(size=(2000, 1000))})
        assert response.status_code == 200, response.content
        assert decoded(response.json()["url"]).size == (MAX_SIDE, 800)
        assert not list(tmp_path.iterdir())

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
    def test_only_real_images_are_accepted(self, staff, name, body):
        response = staff.post(self.URL, {"upload": SimpleUploadedFile(name, body)})
        assert response.status_code == 400
        assert response.json()["error"]["message"]


def test_editor_configs_have_no_nulls():
    """django-ckeditor-5 calls toString() on every config value: one null stops every editor."""
    from django.conf import settings

    def values(node):
        if isinstance(node, dict):
            for value in node.values():
                yield from values(value)
        elif isinstance(node, list):
            for value in node:
                yield from values(value)
        else:
            yield node

    assert None not in list(values(settings.CKEDITOR_5_CONFIGS))
