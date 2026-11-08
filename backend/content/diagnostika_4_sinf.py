"""
Builds diagnostika-4-sinf.json: the diagnostic test for pupils finishing the 4th grade.

    python content/diagnostika_4_sinf.py            # writes the JSON next to this file
    python manage.py import_exam content/diagnostika-4-sinf.json

30 questions, 10 per subject (mathematics, logical thinking, mother tongue). Each subject has
3 easy, 4 medium and 3 hard questions, in that order; 1 point each, 30 at most. Every pupil gets
the same questions, shuffled inside each difficulty group, with shuffled options, so neighbours'
question numbers and answer letters don't match.

The pictures are drawn here as SVG, so they stay sharp at any size and are easy to change: edit a
function below and run the script again. They go into the question text as data: URIs.
"""

import base64
import json
import math
from pathlib import Path

INK = "#1f2a2e"
TEAL = "#17776a"
TEAL_LIGHT = "#d7efe9"
RED = "#d9534f"
BLUE = "#2f6fb5"
AMBER = "#e3a21a"
GRID = "#d5dde0"


# ---------------------------------------------------------------------------- picture helpers


def svg(width: int, height: int, body: str) -> str:
    # A white card behind every picture keeps the drawing readable in the app's dark theme.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" font-family="Arial, Helvetica, sans-serif">'
        f'<rect width="{width}" height="{height}" rx="14" fill="#ffffff"/>{body}</svg>'
    )


def picture(source: str, alt: str) -> str:
    width = source.split('width="', 1)[1].split('"', 1)[0]
    height = source.split('height="', 1)[1].split('"', 1)[0]
    uri = "data:image/svg+xml;base64," + base64.b64encode(source.encode()).decode()
    # class="image": the admin's editor opens it as a block picture that can be resized.
    return (
        f'<figure class="image"><img src="{uri}" alt="{alt}" width="{width}" '
        f'height="{height}"></figure>'
    )


def text(x, y, value, size=18, weight="bold", anchor="middle", fill=INK) -> str:
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}" dominant-baseline="middle" fill="{fill}">{value}</text>'
    )


def clock(hours: int, minutes: int) -> str:
    cx = cy = 130
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="112" fill="#fdfaf3" stroke="{INK}" stroke-width="6"/>'
    ]
    for tick in range(60):
        angle = math.radians(tick * 6)
        inner = 98 if tick % 5 == 0 else 103
        x1, y1 = cx + inner * math.sin(angle), cy - inner * math.cos(angle)
        x2, y2 = cx + 108 * math.sin(angle), cy - 108 * math.cos(angle)
        width = 3 if tick % 5 == 0 else 1
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{INK}" stroke-width="{width}"/>'
        )
    for number in range(1, 13):
        angle = math.radians(number * 30)
        parts.append(
            text(f"{cx + 80 * math.sin(angle):.1f}", f"{cy - 80 * math.cos(angle) + 1:.1f}",
                 number, size=20)
        )  # fmt: skip

    def hand(angle_degrees, length, width, colour):
        angle = math.radians(angle_degrees)
        x, y = cx + length * math.sin(angle), cy - length * math.cos(angle)
        return (
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{colour}" '
            f'stroke-width="{width}" stroke-linecap="round"/>'
        )

    parts.append(hand((hours % 12) * 30 + minutes * 0.5, 46, 9, INK))
    parts.append(hand(minutes * 6, 66, 5, RED))
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="{INK}"/>')
    return svg(260, 260, "".join(parts))


def rectangle() -> str:
    body = (
        f'<rect x="70" y="50" width="240" height="150" fill="{TEAL_LIGHT}" '
        f'stroke="{TEAL}" stroke-width="5"/>'
        # right-angle marks
        f'<path d="M70 68 h18 v-18" fill="none" stroke="{TEAL}" stroke-width="2"/>'
        f'<path d="M292 50 v18 h18" fill="none" stroke="{TEAL}" stroke-width="2"/>'
        + text(190, 30, "8 sm")
        + text(36, 125, "5 sm")
    )
    return svg(360, 230, body)


def fraction_circle(parts_total: int, shaded: int) -> str:
    cx = cy = 115
    r = 95
    shapes = []
    for k in range(parts_total):
        a1 = math.radians(k * 360 / parts_total)
        a2 = math.radians((k + 1) * 360 / parts_total)
        x1, y1 = cx + r * math.sin(a1), cy - r * math.cos(a1)
        x2, y2 = cx + r * math.sin(a2), cy - r * math.cos(a2)
        fill = AMBER if k < shaded else "#ffffff"
        shapes.append(
            f'<path d="M{cx} {cy} L{x1:.1f} {y1:.1f} A{r} {r} 0 0 1 {x2:.1f} {y2:.1f} Z" '
            f'fill="{fill}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
        )
    return svg(230, 230, "".join(shapes))


def bar_chart() -> str:
    days = [("Dushanba", 40), ("Seshanba", 25), ("Chorshanba", 35), ("Payshanba", 50),
            ("Juma", 30)]  # fmt: skip
    base, scale, left = 250, 3.6, 70
    parts = [text(250, 26, "Do‘konda sotilgan olma (kg)", size=17)]
    for value in range(0, 51, 10):
        y = base - value * scale
        parts.append(
            f'<line x1="{left - 6}" y1="{y}" x2="470" y2="{y}" stroke="{GRID}" stroke-width="1"/>'
        )
        parts.append(text(left - 14, y, value, size=13, weight="normal", anchor="end"))
    for i, (day, value) in enumerate(days):
        x = left + 22 + i * 80
        height = value * scale
        parts.append(
            f'<rect x="{x}" y="{base - height}" width="44" height="{height}" rx="4" fill="{TEAL}"/>'
        )
        parts.append(text(x + 22, base - height - 12, value, size=15))
        parts.append(text(x + 22, base + 18, day, size=13, weight="normal"))
    parts.append(
        f'<line x1="{left}" y1="{base}" x2="470" y2="{base}" stroke="{INK}" stroke-width="2"/>'
    )
    return svg(490, 285, "".join(parts))


def l_shape() -> str:
    body = (
        f'<path d="M50 40 H330 V124 H218 V208 H50 Z" fill="{TEAL_LIGHT}" stroke="{TEAL}" '
        f'stroke-width="5" stroke-linejoin="round"/>'
        + text(190, 22, "10 sm")
        + text(22, 124, "6 sm", anchor="middle")
        + text(362, 82, "3 sm")
        + text(274, 146, "4 sm")
    )
    return svg(400, 235, body)


def shape(kind: str, cx: float, cy: float, size: float = 30) -> str:
    half = size / 2
    if kind == "circle":
        return f'<circle cx="{cx}" cy="{cy}" r="{half}" fill="{TEAL}"/>'
    if kind == "square":
        return (
            f'<rect x="{cx - half}" y="{cy - half}" width="{size}" height="{size}" fill="{BLUE}"/>'
        )
    return (
        f'<path d="M{cx} {cy - half} L{cx + half + 2} {cy + half} L{cx - half - 2} {cy + half} Z" '
        f'fill="{AMBER}"/>'
    )


def pattern() -> str:
    sequence = ["circle", "triangle", "square"] * 2 + ["circle", "triangle"]
    parts = []
    for i, kind in enumerate(sequence):
        parts.append(shape(kind, 40 + i * 52, 45))
    x = 40 + len(sequence) * 52
    parts.append(
        f'<rect x="{x - 20}" y="25" width="40" height="40" rx="6" fill="none" stroke="{INK}" '
        f'stroke-width="2" stroke-dasharray="5 4"/>'
    )
    parts.append(text(x, 46, "?", size=24))
    return svg(x + 40, 90, "".join(parts))


def triangles() -> str:
    body = (
        f'<path d="M150 22 L280 200 L20 200 Z" fill="{TEAL_LIGHT}" stroke="{TEAL}" '
        f'stroke-width="4" stroke-linejoin="round"/>'
        f'<line x1="150" y1="22" x2="110" y2="200" stroke="{TEAL}" stroke-width="4"/>'
        f'<line x1="150" y1="22" x2="196" y2="200" stroke="{TEAL}" stroke-width="4"/>'
    )
    return svg(300, 222, body)


def scales() -> str:
    def cube(cx, bottom):
        return f'<rect x="{cx - 12}" y="{bottom - 24}" width="24" height="24" fill="{BLUE}"/>'

    def ball(cx, bottom):
        return f'<circle cx="{cx}" cy="{bottom - 12}" r="12" fill="{RED}"/>'

    def pyramid(cx, bottom):
        return (
            f'<path d="M{cx} {bottom - 30} L{cx + 17} {bottom} L{cx - 17} {bottom} Z" '
            f'fill="{AMBER}"/>'
        )

    def balance(x0, left, right):
        parts = [
            f'<rect x="{x0 + 110}" y="182" width="40" height="10" rx="3" fill="{INK}"/>',
            f'<line x1="{x0 + 130}" y1="182" x2="{x0 + 130}" y2="60" stroke="{INK}" '
            f'stroke-width="5"/>',
            f'<line x1="{x0 + 45}" y1="60" x2="{x0 + 215}" y2="60" stroke="{INK}" stroke-width="5" '
            f'stroke-linecap="round"/>',
            f'<circle cx="{x0 + 130}" cy="60" r="6" fill="{INK}"/>',
        ]
        for centre, items in ((x0 + 45, left), (x0 + 215, right)):
            parts.append(
                f'<path d="M{centre} 60 L{centre - 40} 130 M{centre} 60 L{centre + 40} 130" '
                f'stroke="#7a8a90" stroke-width="2"/>'
            )
            parts.append(
                f'<path d="M{centre - 44} 130 Q{centre} 150 {centre + 44} 130 Z" fill="#c9d3d6" '
                f'stroke="{INK}" stroke-width="2"/>'
            )
            step = 27
            start = centre - (len(items) - 1) * step / 2
            for i, draw in enumerate(items):
                parts.append(draw(start + i * step, 132))
        return "".join(parts)

    body = (
        balance(0, [cube], [ball, ball])
        + balance(270, [pyramid], [cube, cube, cube])
        + text(130, 214, "1-tarozi", size=15, weight="normal")
        + text(400, 214, "2-tarozi", size=15, weight="normal")
    )
    return svg(530, 230, body)


def cube_net() -> str:
    cells = {1: (0, 0), 2: (1, 0), 3: (1, 1), 4: (2, 1), 5: (2, 2), 6: (3, 2)}
    size, pad = 62, 20
    parts = []
    for number, (col, row) in cells.items():
        x, y = pad + col * size, pad + row * size
        parts.append(
            f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{TEAL_LIGHT}" '
            f'stroke="{TEAL}" stroke-width="3"/>'
        )
        parts.append(text(x + size / 2, y + size / 2 + 1, number, size=28))
    return svg(pad * 2 + 4 * size, pad * 2 + 3 * size, "".join(parts))


# ---------------------------------------------------------------------------- questions

NBSP = " "


def q(subject, difficulty, prompt, options, explanation, passage=""):
    """`options`: (content, is_correct) pairs; letters are given in this order."""
    return {
        "subject": subject,
        "difficulty": difficulty,
        "prompt": prompt,
        "passage": passage,
        "explanation": explanation,
        "options": [
            {"label": "ABCD"[i], "content": f"<p>{content}</p>", "isCorrect": correct}
            for i, (content, correct) in enumerate(options)
        ],
    }


EASY, MEDIUM, HARD = 1, 2, 3

MATH = [
    q("math", EASY,
      f"<p>Hisoblang: <b>4{NBSP}508 + 2{NBSP}397</b></p>",
      [(f"6{NBSP}805", False), (f"6{NBSP}905", True), (f"6{NBSP}895", False),
       (f"7{NBSP}905", False)],
      f"<p>4{NBSP}508 + 2{NBSP}397 = 6{NBSP}905.</p>"),
    q("math", EASY,
      "<p>Soat necha bo‘ldi?</p>" + picture(clock(3, 45), "Strelkali soat"),
      [("9:15", False), ("4:45", False), ("3:45", True), ("3:09", False)],
      "<p>Kichik strelka 3 bilan 4 orasida, katta strelka 9 da turibdi: 3 soat 45 daqiqa.</p>"),
    q("math", EASY,
      "<p><b>1 m 25 sm</b> necha santimetrga teng?</p>",
      [("125 sm", True), (f"1{NBSP}025 sm", False), (f"1{NBSP}250 sm", False), ("152 sm", False)],
      "<p>1 m = 100 sm, demak 100 sm + 25 sm = 125 sm.</p>"),
    q("math", MEDIUM,
      "<p>To‘g‘ri to‘rtburchakning perimetrini toping.</p>"
      + picture(rectangle(), "Tomonlari 8 sm va 5 sm bo‘lgan to‘g‘ri to‘rtburchak"),
      [("40 sm", False), ("13 sm", False), ("21 sm", False), ("26 sm", True)],
      "<p>P = (8 + 5) · 2 = 26 sm. 40 — bu yuza (sm²), perimetr emas.</p>"),
    q("math", MEDIUM,
      "<p>Ifodaning qiymatini toping: <b>120 − 40 : 8 · 3</b></p>",
      [("30", False), ("105", True), ("345", False), ("115", False)],
      "<p>Avval bo‘lish va ko‘paytirish: 40 : 8 = 5, 5 · 3 = 15. "
      "Keyin ayirish: 120 − 15 = 105.</p>"),
    q("math", MEDIUM,
      "<p>Doiraning qancha qismi bo‘yalgan?</p>"
      + picture(fraction_circle(8, 3), "Teng bo‘laklarga bo‘lingan doira"),
      [(r"$\frac{3}{5}$", False), (r"$\frac{5}{8}$", False), (r"$\frac{3}{8}$", True),
       (r"$\frac{1}{3}$", False)],
      "<p>Doira 8 ta teng bo‘lakka bo‘lingan, ulardan 3 tasi bo‘yalgan: 3/8.</p>"),
    q("math", MEDIUM,
      "<p>Do‘konga 6 quti olma keltirildi, har bir qutida 24 kg olma bor. Kun davomida 85 kg "
      "olma sotildi. Do‘konda necha kilogramm olma qoldi?</p>",
      [("59 kg", True), ("69 kg", False), ("229 kg", False), ("49 kg", False)],
      "<p>6 · 24 = 144 kg keltirilgan. 144 − 85 = 59 kg qoldi.</p>"),
    q("math", HARD,
      "<p>Ikki shahar orasidagi masofa 360 km. Bu shaharlardan bir vaqtda bir-biriga qarab ikki "
      "avtomobil yo‘lga chiqdi. Birinchisining tezligi soatiga 70 km, ikkinchisiniki soatiga "
      "50 km. Ular necha soatdan keyin uchrashadi?</p>",
      [("18 soatdan keyin", False), ("6 soatdan keyin", False), ("4 soatdan keyin", False),
       ("3 soatdan keyin", True)],
      "<p>Ular bir soatda bir-biriga 70 + 50 = 120 km yaqinlashadi. 360 : 120 = 3 soat.</p>"),
    q("math", HARD,
      "<p>Diagrammada do‘konda besh kun davomida sotilgan olma ko‘rsatilgan. Dushanba va "
      "seshanba kunlari birgalikda sotilgan olma payshanbada sotilgan olmadan necha kilogramm "
      "ko‘p?</p>" + picture(bar_chart(), "Kunlar bo‘yicha sotilgan olma diagrammasi"),
      [("65 kg", False), ("15 kg", True), ("10 kg", False), ("25 kg", False)],
      "<p>Dushanba va seshanba: 40 + 25 = 65 kg. Payshanba: 50 kg. 65 − 50 = 15 kg.</p>"),
    q("math", HARD,
      "<p>Shaklning yuzini toping.</p>"
      + picture(l_shape(), "To‘g‘ri to‘rtburchakdan burchagi kesib olingan shakl"),
      [("60 sm²", False), ("32 sm²", False), ("48 sm²", True), ("36 sm²", False)],
      "<p>Butun to‘g‘ri to‘rtburchak: 10 · 6 = 60 sm². Kesilgan qismi: 4 · 3 = 12 sm². "
      "60 − 12 = 48 sm². (32 sm — bu shaklning perimetri.)</p>"),
]  # fmt: skip

LOGIC = [
    q("iq", EASY,
      "<p>Qonuniyatni toping va qatorni davom ettiring: <b>3, 7, 11, 15, …</b></p>",
      [("18", False), ("20", False), ("19", True), ("21", False)],
      "<p>Har bir son oldingisidan 4 ga katta: 15 + 4 = 19.</p>"),
    q("iq", EASY,
      "<p>So‘roq belgisi o‘rnida qaysi shakl turishi kerak?</p>"
      + picture(pattern(), "Rangli shakllar qatori, oxirida so‘roq belgisi"),
      [("Kvadrat", True), ("Doira", False), ("Uchburchak", False), ("Yulduzcha", False)],
      "<p>Shakllar «doira, uchburchak, kvadrat» tartibida takrorlanadi. Uchburchakdan keyin "
      "kvadrat keladi.</p>"),
    q("iq", EASY,
      "<p>Qaysi so‘z ortiqcha?</p>",
      [("olma", False), ("nok", False), ("o‘rik", False), ("sabzi", True)],
      "<p>Olma, nok va o‘rik — mevalar, sabzi esa sabzavot.</p>"),
    q("iq", MEDIUM,
      "<p>Rasmda nechta uchburchak bor?</p>"
      + picture(triangles(), "Ichidan ikkita chiziq o‘tkazilgan katta uchburchak"),
      [("3 ta", False), ("4 ta", False), ("5 ta", False), ("6 ta", True)],
      "<p>3 ta kichik uchburchak, ikkita qo‘shni bo‘lakdan iborat 2 ta uchburchak va 1 ta katta "
      "uchburchak: 3 + 2 + 1 = 6.</p>"),
    q("iq", MEDIUM,
      "<p>Juftlikdagi bog‘lanishni toping: <b>kitob — o‘qish</b>, <b>qalam — ?</b></p>",
      [("daftar", False), ("yozish", True), ("qog‘oz", False), ("maktab", False)],
      "<p>Kitob o‘qish uchun, qalam esa yozish uchun kerak.</p>"),
    q("iq", MEDIUM,
      "<p>Ali Validan baland. Vali Sardordan baland. Sardor Bekzoddan baland. Bo‘yi bo‘yicha "
      "(eng balanddan boshlab sanaganda) ikkinchi o‘rinda kim turadi?</p>",
      [("Ali", False), ("Sardor", False), ("Vali", True), ("Bekzod", False)],
      "<p>Balanddan pastga: Ali, Vali, Sardor, Bekzod. Ikkinchi — Vali.</p>"),
    q("iq", MEDIUM,
      "<p>Ikkala tarozi ham muvozanatda. Bitta piramida nechta sharga teng?</p>"
      + picture(scales(), "Ikkita tarozi: kub, shar va piramidalar"),
      [("6 ta", True), ("5 ta", False), ("3 ta", False), ("2 ta", False)],
      "<p>1-tarozi: 1 kub = 2 shar. 2-tarozi: 1 piramida = 3 kub = 3 · 2 = 6 shar.</p>"),
    q("iq", HARD,
      "<p>Qonuniyatni toping va qatorni davom ettiring: <b>2, 3, 5, 9, 17, …</b></p>",
      [("25", False), ("32", False), ("33", True), ("34", False)],
      "<p>Ayirmalar har safar ikki baravar ortadi: +1, +2, +4, +8, keyin +16. 17 + 16 = 33.</p>"),
    q("iq", HARD,
      "<p>Rasmdagi yoyilmadan kub yasaldi. Kubning <b>2</b> raqami yozilgan yog‘i qarshisida "
      "qaysi raqam bo‘ladi?</p>" + picture(cube_net(), "Raqamlangan kub yoyilmasi"),
      [("3", False), ("4", False), ("6", False), ("5", True)],
      "<p>3 ni kubning tagi deb olsak: 2 — orqa, 5 — old, 1 — chap, 4 — o‘ng, 6 — ust yoq "
      "bo‘ladi. Orqa va old yoqlar qarama-qarshi: 2 va 5.</p>"),
    q("iq", HARD,
      "<p>Anvar, Bobur va Jasur qizil, ko‘k va yashil rangli kurtkalar kiyib olishgan, har "
      "birida bittadan. Anvar qizil kurtka kiymagan. Bobur ko‘k ham, qizil ham kiymagan. Jasur "
      "qanday rangli kurtka kiygan?</p>",
      [("Ko‘k", False), ("Qizil", True), ("Yashil", False), ("Aniqlab bo‘lmaydi", False)],
      "<p>Bobur ko‘k ham, qizil ham emas — demak yashil. Anvar qizil emas, yashil esa Boburda — "
      "demak ko‘k. Jasurga qizil qoladi.</p>"),
]  # fmt: skip

STORK = (
    "<p>Kuz kirib, kunlar salqinlasha boshladi. Laylakning bolalari ulg‘ayib, uchishni o‘rganib "
    "olishdi. Bir kuni ertalab laylaklar to‘da bo‘lib osmonga ko‘tarilishdi va uzoq, issiq "
    "o‘lkalar tomon uchib ketishdi. Bahor kelib, havo isigach, ular yana o‘z uyalariga qaytib "
    "kelishadi.</p>"
)

LANGUAGE = [
    q("language", EASY,
      "<p>Qaysi so‘z unli tovush bilan boshlangan?</p>",
      [("kitob", False), ("olma", True), ("daftar", False), ("maktab", False)],
      "<p>«Olma» so‘zi «o» unli tovushi bilan boshlangan.</p>"),
    q("language", EASY,
      "<p><b>Issiq</b> so‘zining zid ma’noli (antonim) so‘zini toping.</p>",
      [("iliq", False), ("qaynoq", False), ("sovuq", True), ("yoz", False)],
      "<p>Issiq — sovuq. «Iliq» va «qaynoq» ma’nosi yaqin so‘zlar.</p>"),
    q("language", EASY,
      "<p><b>Chiroyli</b> so‘zining ma’nodosh (sinonim) so‘zini toping.</p>",
      [("go‘zal", True), ("xunuk", False), ("katta", False), ("tez", False)],
      "<p>Chiroyli — go‘zal. «Xunuk» esa uning zid ma’nolisi.</p>"),
    q("language", MEDIUM,
      "<p>Qaysi qatorda faqat fe’llar berilgan?</p>",
      [("kitob, yozdi, qizil", False), ("chiroyli, katta, baland", False),
       ("yugurdi, o‘qidi, yozmoq", True), ("uch, beshta, o‘n", False)],
      "<p>Yugurdi, o‘qidi, yozmoq — harakatni bildiradi, «nima qildi?», «nima qilmoq?» "
      "so‘roqlariga javob beradi.</p>"),
    q("language", MEDIUM,
      "<p><b>Maktabga</b> so‘zi qaysi kelishikda turibdi?</p>",
      [("o‘rin-payt kelishigida", False), ("jo‘nalish kelishigida", True),
       ("chiqish kelishigida", False), ("tushum kelishigida", False)],
      "<p>-ga qo‘shimchasi jo‘nalish kelishigining qo‘shimchasi: «qayerga?» so‘rog‘iga javob "
      "beradi.</p>"),
    q("language", MEDIUM,
      "<p>Qaysi so‘z bo‘g‘inlarga to‘g‘ri ajratilgan?</p>",
      [("dar-ax-tlar", False), ("dara-xt-lar", False), ("da-raxt-lar", True),
       ("d-arax-tlar", False)],
      "<p>Har bir bo‘g‘inda bitta unli bo‘ladi: da-raxt-lar.</p>"),
    q("language", MEDIUM,
      "<p>Qaysi so‘z to‘g‘ri yozilgan?</p>",
      [("mustaqilik", False), ("mustakillik", False), ("mustaqillig", False),
       ("mustaqillik", True)],
      "<p>To‘g‘ri yozilishi: mustaqillik (mustaqil + lik).</p>"),
    q("language", HARD,
      "<p>Matnga ko‘ra laylaklar nima uchun uchib ketishdi?</p>",
      [("Kuz kelib, havo sovuy boshlagani uchun", True),
       ("Bolalari uchishni bilmagani uchun", False),
       ("Bahor kelgani uchun", False),
       ("Uyalari buzilib qolgani uchun", False)],
      "<p>Matnda kuz kirib, kunlar salqinlashgani va laylaklar issiq o‘lkalarga uchib ketgani "
      "aytilgan.</p>",
      passage=STORK),
    q("language", HARD,
      "<p>Gapning egasini toping: <b>Kichkina qizcha bog‘da chiroyli gullarni sug‘ordi.</b></p>",
      [("bog‘da", False), ("gullarni", False), ("sug‘ordi", False), ("qizcha", True)],
      "<p>«Kim sug‘ordi?» — qizcha. Ega «kim?» yoki «nima?» so‘rog‘iga javob beradi.</p>"),
    q("language", HARD,
      "<p>Qaysi so‘zda so‘z yasovchi qo‘shimcha bor?</p>",
      [("kitoblar", False), ("paxtakor", True), ("maktabga", False), ("ukamning", False)],
      "<p>«Paxtakor» so‘zi «paxta» so‘ziga -kor qo‘shimchasi qo‘shilib, yangi so‘z yasalgan. "
      "-lar, -ga, -m, -ning esa so‘zning shaklini o‘zgartiradi.</p>"),
]  # fmt: skip


def build() -> dict:
    questions = MATH + LOGIC + LANGUAGE
    for number, question in enumerate(questions, start=1):
        question["number"] = number
        question["type"] = "single_choice"
    return {
        "title": "4-sinf bitiruvchilari uchun diagnostik test",
        "description": "Matematika, mantiqiy fikrlash va ona tili bo‘yicha 30 ta savol. Har bir "
        "to‘g‘ri javob 1 ball, eng yuqori natija 30 ball.",
        "durationMinutes": 60,
        "pointsPerQuestion": 1,
        # Everybody gets the same questions: showing the answers to whoever finishes first
        # would hand them to the pupils who haven't started yet.
        "reviewEnabled": False,
        "shuffleQuestions": True,
        "shuffleOptions": True,
        "grades": [4],
        "sections": [
            {"subject": "math", "title": "Matematika"},
            {"subject": "iq", "title": "Mantiqiy fikrlash"},
            {"subject": "language", "title": "Ona tili"},
        ],
        "questions": questions,
    }


if __name__ == "__main__":
    target = Path(__file__).with_name("diagnostika-4-sinf.json")
    target.write_text(json.dumps(build(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {target}")
