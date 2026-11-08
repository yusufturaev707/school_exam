"""
Question text is written in a rich-text editor and stored as HTML. That HTML ends up inside
children's browsers, so it is cleaned on the way into the database: only the tags below survive.
Links are left out on purpose, because an exam has no business sending a child to another site.

Formulas are plain text inside the HTML, e.g. `<p>Hisoblang: $\\frac{1}{2}$</p>`. Cleaning keeps
them as they are, and the frontend turns them into KaTeX when it displays them.

Images are kept inside the HTML too, as compressed `data:` URIs (see apps/core/images.py). An
image anywhere else (another site, a file on the admin's computer) is refused with a message,
not silently dropped, so the admin never publishes a question whose picture has vanished.
"""

import html
import re

import nh3
from django.core.exceptions import ValidationError
from django.db import models

from .editor_palette import TEXT_COLOURS
from .images import ImageError, inline_image

ALLOWED_TAGS = {
    "p", "br", "hr", "span", "h2", "h3", "h4", "blockquote",
    "strong", "b", "em", "i", "u", "s", "sub", "sup", "mark",
    "ul", "ol", "li",
    "table", "caption", "thead", "tbody", "tfoot", "tr", "th", "td", "colgroup", "col",
    "figure", "figcaption", "img",
}  # fmt: skip

ALLOWED_ATTRIBUTES = {
    "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "ol": {"start"},
    "*": {"style"},
}

# The editor recognises its own images, tables and highlights by these classes when a saved
# question is opened again. Without them a resized picture would lose its size on the next save.
ALLOWED_CLASSES = {
    "figure": {"image", "image_resized", "table"},
    "mark": {"marker-yellow"},
}

# Layout and the editor's few formatting tools. Nothing here can load a URL, and the values of
# the last three are checked in _safe_style.
ALLOWED_STYLES = {
    "text-align", "width", "height", "aspect-ratio",
    "color", "list-style-type", "margin-left",
}  # fmt: skip

LIST_STYLES = {
    "decimal", "decimal-leading-zero", "lower-roman", "upper-roman",
    "lower-latin", "upper-latin", "lower-alpha", "upper-alpha", "disc", "circle", "square",
}  # fmt: skip
INDENT = re.compile(r"(\d{1,3})px")  # the editor indents paragraphs by 40px a step
MAX_INDENT_PX = 200


def _safe_style(style: str) -> str:
    """Keeps a colour only from the editor's palette, and only sane list styles and indents."""
    kept = []
    for declaration in style.split(";"):
        name, _, value = declaration.partition(":")
        name, value = name.strip().lower(), value.strip()
        if not name or not value:
            continue
        if name == "color" and value.lower() not in TEXT_COLOURS:
            continue
        if name == "list-style-type" and value.lower() not in LIST_STYLES:
            continue
        if name == "margin-left":
            indent = INDENT.fullmatch(value)
            if indent is None or int(indent[1]) > MAX_INDENT_PX:
                continue
        kept.append(f"{name}:{value}")
    return ";".join(kept)


# Each image is at most ~400 KB of base64; this caps one text (a prompt, an option) as a whole.
MAX_HTML_CHARS = 1_500_000

IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
HAS_SRC = re.compile(r"\ssrc=", re.IGNORECASE)


def sanitize_html(value: str, problems: list[str] | None = None) -> str:
    """
    Cleans editor HTML and compresses its images. An image that can't be kept is removed; when
    `problems` is given, the reason is appended to it, so callers that report errors can say why.
    """
    refused: list[str] = []

    def keep_safe_attribute(tag: str, attribute: str, value: str) -> str | None:
        if tag == "img" and attribute == "src":
            try:
                return inline_image(value)
            except ImageError as error:
                refused.extend(error.messages)
                return None
        if attribute == "style":
            return _safe_style(value) or None
        return value

    cleaned = nh3.clean(
        value or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        allowed_classes=ALLOWED_CLASSES,
        attribute_filter=keep_safe_attribute,
        # http(s) reach the filter only so it can say why such an image is refused. Other schemes
        # (file:, blob:, javascript:) are dropped by nh3 itself and noticed below.
        url_schemes={"data", "http", "https"},
        filter_style_properties=ALLOWED_STYLES,
        link_rel=None,
    )
    sourceless = 0

    def drop_sourceless(match: re.Match) -> str:
        nonlocal sourceless
        if HAS_SRC.search(match[0]):
            return match[0]
        sourceless += 1
        return ""

    cleaned = IMG_TAG.sub(drop_sourceless, cleaned).strip()
    # nh3 leaves class="" when none of an element's classes is allowed. Text can't contain this
    # literally: nh3 escapes quotes in text.
    cleaned = cleaned.replace(' class=""', "")
    if problems is not None:
        problems.extend(refused)
        if sourceless > len(refused):
            problems.append(
                "Rasm qo‘yilmadi: u kompyuterdagi faylga yoki boshqa joyga havola edi. "
                "Rasmni “Rasm qo‘shish” tugmasi bilan yuklang."
            )
        if len(cleaned) > MAX_HTML_CHARS:
            problems.append(
                "Matndagi rasmlar jami juda katta. Rasmlar sonini yoki o‘lchamini kamaytiring."
            )
    return cleaned


def is_blank_html(value: str) -> bool:
    """True for what editors leave behind when nothing was written, such as `<p>&nbsp;</p>`."""
    if re.search(r"<img\b", value or "", re.IGNORECASE):
        return False
    text = html.unescape(re.sub(r"<[^>]+>", "", value or ""))
    return not text.replace("\xa0", " ").strip()


class RichTextField(models.TextField):
    """
    Holds editor HTML. Cleaning happens here rather than in forms, so the admin, `import_exam` and
    any other code that saves a model all go through it. The one exception is `QuerySet.update()`,
    which skips model fields: never use it to write these columns.
    """

    def clean(self, value, model_instance):
        cleaned = self._cleaned(value)
        return super().clean("" if is_blank_html(cleaned) else cleaned, model_instance)

    def pre_save(self, model_instance, add):
        # After clean() this is cheap: images that are already compressed are only checked.
        cleaned = self._cleaned(getattr(model_instance, self.attname))
        setattr(model_instance, self.attname, cleaned)
        return cleaned

    def _cleaned(self, value) -> str:
        problems: list[str] = []
        cleaned = sanitize_html(value, problems)
        if problems:
            raise ValidationError(list(dict.fromkeys(problems)))
        return cleaned

    def formfield(self, **kwargs):
        # Imported here because the widget needs Django's settings to be ready.
        from django_ckeditor_5.widgets import CKEditor5Widget

        # The admin passes its own textarea widget for every TextField: replace it, but keep an
        # editor widget chosen on purpose (QuestionAdmin gives the prompt the "extended" toolbar).
        widget = kwargs.get("widget")
        if not isinstance(widget, CKEditor5Widget):
            widget = CKEditor5Widget()
        return super().formfield(**{**kwargs, "widget": widget})
