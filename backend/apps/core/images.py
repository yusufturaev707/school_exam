"""
Question images live inside the question HTML as `data:` URIs, so a question is one self-contained
record. Nothing has to be backed up next to the database, and there are no public /media/ files a
pupil could open by guessing a name before the exam.

The price is size: base64 adds a third, and the HTML travels to every pupil in the class at once.
So every raster image is re-encoded on the way in:
- scaled down to at most MAX_SIDE pixels on its longer side;
- stripped of metadata (a phone photo's EXIF can hold the place where it was taken);
- saved as WebP, lossy or lossless, whichever is smaller. Lossless wins for diagrams and charts and
  keeps their lines sharp; lossy wins for photos.

An image that is already in that shape is kept byte for byte, so saving a question again never
recompresses, and slowly blurs, its pictures. Animated GIFs keep only their first frame.
SVG images (data:image/svg+xml) are kept as written: they are text, already small, and a browser
runs no scripts in an SVG shown through <img>.
"""

import base64
import binascii
import io
import re

from django.core.exceptions import ValidationError
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_SIDE = 1600  # px; sharp on a laptop screen and in the zoomed view
MAX_IMAGE_BYTES = 300 * 1024  # one image after compression
MAX_SOURCE_BYTES = 10 * 1024 * 1024  # what may come in before compression
MAX_SOURCE_PIXELS = 40_000_000  # refused before decoding: a tiny file can unpack to gigabytes
MAX_SVG_CHARS = 100_000
# Diagrams, charts and screenshots of text have few colours; only those are tried losslessly.
FEW_COLOURS = 4096
# (longer side, WebP quality), tried in order until the result fits MAX_IMAGE_BYTES. Ordinary
# photos and diagrams fit at the first step; the later ones are for very busy, detailed pictures.
ATTEMPTS = ((MAX_SIDE, 82), (1200, 72), (1000, 60), (800, 50))

RASTER_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}
DATA_URI = re.compile(
    r"data:(?P<mime>image/[a-z0-9.+-]+)(?P<params>(?:;[^;,]*)*?)(?P<base64>;base64)?,(?P<data>.*)",
    re.IGNORECASE | re.DOTALL,
)


class ImageError(ValidationError):
    """An image that can't go into a question. The message is shown to the admin as is."""


def data_uri(webp: bytes) -> str:
    return "data:image/webp;base64," + base64.b64encode(webp).decode("ascii")


def inline_image(src: str) -> str:
    """Returns the `src` an <img> in question HTML should have, or raises ImageError."""
    match = DATA_URI.fullmatch(src.strip())
    if match is None:
        raise ImageError(
            "Rasm boshqa saytdan olingan havola ko‘rinishida. Rasmni kompyuterga saqlab, "
            "“Rasm qo‘shish” tugmasi bilan yuklang."
        )
    if match["mime"].lower() == "image/svg+xml":
        if len(src) > MAX_SVG_CHARS:
            raise ImageError("SVG rasm juda katta (100 KB dan ortiq).")
        return src
    if not match["base64"]:
        raise ImageError("Rasm buzilgan: uni qaytadan qo‘ying.")
    try:
        raw = base64.b64decode(re.sub(r"\s+", "", match["data"]), validate=True)
    except (binascii.Error, ValueError):
        raise ImageError("Rasm buzilgan: uni qaytadan qo‘ying.") from None
    if _already_compressed(raw):
        return data_uri(raw)
    return data_uri(compress_image(raw))


def compress_image(raw: bytes) -> bytes:
    """Any accepted raster image in, a small metadata-free WebP out."""
    if len(raw) > MAX_SOURCE_BYTES:
        raise ImageError("Rasm fayli juda katta (10 MB dan ortiq).")
    image = _open(raw)
    image = ImageOps.exif_transpose(image)  # a phone photo stays the right way up
    image = _without_metadata(_plain_mode(image))
    few_colours = image.getcolors(FEW_COLOURS) is not None
    for side, quality in ATTEMPTS:
        if max(image.size) > side:
            image.thumbnail((side, side), Image.Resampling.LANCZOS)
        encoded = _webp(image, quality)
        if few_colours:
            encoded = min(encoded, _webp(image, lossless=True), key=len)
        if len(encoded) <= MAX_IMAGE_BYTES:
            return encoded
    raise ImageError("Rasm siqilgandan keyin ham juda katta. Kichikroq yoki soddaroq rasm tanlang.")


def _open(raw: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(raw))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ImageError("Bu fayl rasm emas yoki buzilgan.") from None
    if image.format not in RASTER_FORMATS:
        raise ImageError("Faqat JPG, PNG, GIF yoki WebP rasm qo‘yish mumkin.")
    width, height = image.size
    if width * height > MAX_SOURCE_PIXELS:
        raise ImageError("Rasm o‘lchami juda katta (40 megapikseldan ortiq).")
    try:
        image.load()
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise ImageError("Rasm buzilgan yoki oxirigacha yuklanmagan.") from None
    return image


def _plain_mode(image: Image.Image) -> Image.Image:
    transparent = image.mode in ("RGBA", "LA", "PA") or (
        image.mode == "P" and "transparency" in image.info
    )
    if not transparent:
        return image.convert("RGB")
    image = image.convert("RGBA")
    # PNGs often carry an alpha channel that is opaque everywhere: dropping it saves bytes.
    if image.getextrema()[3][0] == 255:
        return image.convert("RGB")
    return image


def _without_metadata(image: Image.Image) -> Image.Image:
    image.info = {}
    return image


def _webp(image: Image.Image, quality: int = 80, lossless: bool = False) -> bytes:
    buffer = io.BytesIO()
    # For lossless, "quality" is how hard the encoder tries, not how much it throws away.
    image.save(buffer, "WEBP", quality=quality, lossless=lossless, method=4)
    return buffer.getvalue()


def _already_compressed(raw: bytes) -> bool:
    """True for a WebP this module would keep: right size, no metadata, decodes cleanly."""
    if len(raw) > MAX_IMAGE_BYTES:
        return False
    try:
        image = Image.open(io.BytesIO(raw))
        if image.format != "WEBP" or getattr(image, "is_animated", False):
            return False
        if max(image.size) > MAX_SIDE or {"exif", "xmp", "icc_profile"} & image.info.keys():
            return False
        image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        return False
    return True
