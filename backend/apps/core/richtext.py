"""
Question text is written in a rich-text editor and stored as HTML. That HTML ends up inside
children's browsers, so it is cleaned on the way into the database: only the tags below survive.
Links are left out on purpose, because an exam has no business sending a child to another site.

Formulas are plain text inside the HTML, e.g. `<p>Hisoblang: $\\frac{1}{2}$</p>`. Cleaning keeps
them as they are, and the frontend turns them into KaTeX when it displays them.
"""

import html
import re

import nh3
from django.db import models

ALLOWED_TAGS = {
    "p", "br", "hr", "span", "h2", "h3", "h4", "blockquote",
    "strong", "b", "em", "i", "u", "s", "sub", "sup",
    "ul", "ol", "li",
    "table", "caption", "thead", "tbody", "tfoot", "tr", "th", "td", "colgroup", "col",
    "figure", "figcaption", "img",
}  # fmt: skip

ALLOWED_ATTRIBUTES = {
    "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "*": {"style"},
}

# Only layout: the editor sets these for alignment and image size. Nothing can load a URL.
ALLOWED_STYLES = {"text-align", "width", "height", "aspect-ratio"}

SAFE_IMAGE_SOURCE = re.compile(r"^(https?://|/|data:image/)", re.IGNORECASE)


def _keep_safe_attribute(tag: str, attribute: str, value: str) -> str | None:
    if tag == "img" and attribute == "src" and not SAFE_IMAGE_SOURCE.match(value):
        return None
    return value


def sanitize_html(value: str) -> str:
    return nh3.clean(
        value or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        attribute_filter=_keep_safe_attribute,
        url_schemes={"http", "https", "data"},
        filter_style_properties=ALLOWED_STYLES,
        link_rel=None,
    ).strip()


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
        cleaned = sanitize_html(value)
        return super().clean("" if is_blank_html(cleaned) else cleaned, model_instance)

    def pre_save(self, model_instance, add):
        cleaned = sanitize_html(getattr(model_instance, self.attname))
        setattr(model_instance, self.attname, cleaned)
        return cleaned

    def formfield(self, **kwargs):
        # Imported here because the widget needs Django's settings to be ready.
        from django_ckeditor_5.widgets import CKEditor5Widget

        # Set last: the admin passes its own textarea widget for every TextField.
        return super().formfield(**{**kwargs, "widget": CKEditor5Widget()})
