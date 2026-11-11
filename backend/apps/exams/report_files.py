"""
The results report (apps.exams.reports) as files to download: JSON, Excel, PDF and a PNG picture.

PDF and PNG need a TrueType font that has Uzbek letters (o‘, g‘). On Debian that is DejaVu Sans
(`apt install fonts-dejavu-core`, usually already there); on Windows Arial. Without either the
font bundled with reportlab is used, which covers Uzbek Latin but not Cyrillic.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from functools import cache
from io import BytesIO

from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify

FORMATS = {
    "json": ("application/json; charset=utf-8", "json"),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
    "pdf": ("application/pdf", "pdf"),
    "png": ("image/png", "png"),
}

BRAND = "#1f6f5f"
BRAND_SOFT = "#d3efe5"
INK = "#191c1b"
INK_SOFT = "#414946"
LINE = "#c1c9c5"
SURFACE = "#f1f5f3"
BAND_COLORS = {"high": "#1f6f3f", "mid": "#8a5300", "growing": "#ba1a1a"}
BAND_SOFT = {"high": "#c6efd3", "mid": "#ffe3bd", "growing": "#ffdad6"}


def render(report: dict, file_format: str) -> bytes:
    return {"json": to_json, "xlsx": to_xlsx, "pdf": to_pdf, "png": to_png}[file_format](report)


def file_name(report: dict, file_format: str) -> str:
    name = slugify(report["exam"]["title"]) or "imtihon"
    return f"{name}-natijalar-{timezone.localdate():%Y-%m-%d}.{FORMATS[file_format][1]}"


# ------------------------------------------------------------------------------- formatting


def percent(value) -> str:
    return "—" if value is None else f"{value:.1f}".replace(".", ",") + "%"


def number(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.1f}".replace(".", ",")
    return f"{int(value):,}".replace(",", " ")


def when(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M")


def filters_text(report: dict, *, with_exam: bool = True) -> str:
    """The filters for people. Under a title that already names the exam, without the exam."""
    items = report["filters"] if with_exam else report["filters"][1:]
    parts = [f"{item['label']}: {item['value']}" for item in items]
    return "; ".join(parts) or "Barcha o‘quvchilar"


def summary_rows(report: dict) -> list[tuple[str, str]]:
    summary = report["summary"]
    exam = report["exam"]
    if not summary.get("count"):
        return [("Natijalar", "yo‘q")]
    return [
        ("Natijasi bor o‘quvchilar", number(summary["count"])),
        ("O‘rtacha natija", percent(summary["averagePercent"])),
        ("Mediana", percent(summary["medianPercent"])),
        ("Eng yuqori natija", percent(summary["maxPercent"])),
        ("Eng past natija", percent(summary["minPercent"])),
        ("Standart chetlanish", percent(summary["stdevPercent"])),
        ("O‘rtacha ball", f"{number(summary['averageScore'])} / {exam['maxScore']}"),
        (
            "O‘rtacha to‘g‘ri javoblar",
            f"{number(summary['averageCorrect'])} / {exam['questionCount']}",
        ),
        ("O‘rtacha sarflangan vaqt", f"{number(summary['averageDurationMinutes'])} daqiqa"),
        ("O‘zi yakunlagan", number(summary["finishedManually"])),
        ("Vaqt tugab yakunlangan", number(summary["finishedByTimeout"])),
    ]


# ------------------------------------------------------------------------------------- JSON


def to_json(report: dict) -> bytes:
    return json.dumps(report, ensure_ascii=False, indent=1).encode("utf-8")


# ------------------------------------------------------------------------------------ Excel


def to_xlsx(report: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    from openpyxl.formatting.rule import ColorScaleRule
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    from apps.core.sheets import EXCEL_CELL_LIMIT

    header_font = Font(bold=True, color="0B3A30")
    header_fill = PatternFill("solid", fgColor="D3EFE5")

    def clean(value):
        if isinstance(value, str):
            return ILLEGAL_CHARACTERS_RE.sub("", value)[:EXCEL_CELL_LIMIT]
        return value

    def write_table(sheet, start_row, headers, rows, formats=None):
        formats = formats or {}
        for column, header in enumerate(headers, start=1):
            cell = sheet.cell(row=start_row, column=column, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        for line, row in enumerate(rows, start=start_row + 1):
            for column, value in enumerate(row, start=1):
                cell = sheet.cell(row=line, column=column, value=clean(value))
                if isinstance(value, str) and value.startswith("="):
                    cell.data_type = "s"  # a name that only looks like a formula stays text
                if column in formats:
                    cell.number_format = formats[column]
        return start_row + len(rows)

    def fit(sheet, headers, rows, widest=48):
        for column, header in enumerate(headers, start=1):
            values = [len(str(header))] + [len(str(row[column - 1] or "")) for row in rows[:500]]
            sheet.column_dimensions[get_column_letter(column)].width = min(max(values) + 2, widest)

    def percent_scale(sheet, column, first, last):
        if last < first:
            return
        letter = get_column_letter(column)
        sheet.conditional_formatting.add(
            f"{letter}{first}:{letter}{last}",
            ColorScaleRule(
                start_type="num",
                start_value=0,
                start_color="FFDAD6",
                mid_type="num",
                mid_value=50,
                mid_color="FFE3BD",
                end_type="num",
                end_value=100,
                end_color="C6EFD3",
            ),
        )

    exam = report["exam"]
    book = Workbook()

    # --- summary
    sheet = book.active
    sheet.title = "Umumiy"
    sheet["A1"] = exam["title"]
    sheet["A1"].font = Font(bold=True, size=14, color="1F6F5F")
    sheet["A2"] = f"Filtrlar: {filters_text(report)}"
    sheet["A3"] = f"Tuzilgan vaqti: {when(report['generatedAt'])}"
    sheet["A4"] = (
        f"{exam['questionCount']} ta savol, {exam['durationMinutes']} daqiqa, "
        f"maksimal ball {exam['maxScore']}"
    )
    row = write_table(sheet, 6, ["Ko‘rsatkich", "Qiymat"], summary_rows(report)) + 2
    row = (
        write_table(
            sheet,
            row,
            ["Natija oralig‘i (%)", "O‘quvchilar soni"],
            [(item["label"], item["count"]) for item in report["distribution"]],
        )
        + 2
    )
    write_table(
        sheet,
        row,
        ["Daraja", "Oraliq", "O‘quvchilar soni"],
        [(item["label"], item["range"], item["count"]) for item in report["bands"]],
    )
    sheet.column_dimensions["A"].width = 30
    sheet.column_dimensions["B"].width = 20
    sheet.column_dimensions["C"].width = 18

    # --- pupils
    subjects = report["subjectColumns"]
    headers = [
        "O‘rin",
        "F.I.Sh.",
        "Viloyat",
        "Tuman",
        "Maktab",
        "Sinf",
        "To‘g‘ri",
        "Noto‘g‘ri",
        "Javobsiz",
        "Ball",
        "Maks. ball",
        "Foiz (%)",
        *[f"{subject['name']} (%)" for subject in subjects],
        "Yakunlash",
        "Boshlagan",
        "Yakunlagan",
        "Sarflangan vaqt (daq.)",
    ]
    rows = [
        [
            pupil["rank"],
            pupil["name"],
            pupil["region"],
            pupil["district"],
            pupil["school"],
            pupil["classroom"],
            pupil["correct"],
            pupil["incorrect"],
            pupil["unanswered"],
            pupil["score"],
            pupil["maxScore"],
            pupil["percent"],
            *[pupil["subjects"].get(subject["code"]) for subject in subjects],
            pupil["finishReason"],
            datetime.fromisoformat(pupil["startedAt"]).replace(tzinfo=None),
            datetime.fromisoformat(pupil["completedAt"]).replace(tzinfo=None),
            pupil["durationMinutes"],
        ]
        for pupil in report["pupils"]
    ]
    sheet = book.create_sheet("O‘quvchilar")
    percent_columns = [12 + index for index in range(len(subjects) + 1)]
    date_columns = [len(headers) - 2, len(headers) - 1]
    formats = {column: "0.0" for column in percent_columns}
    formats.update({column: "dd.mm.yyyy hh:mm" for column in date_columns})
    formats[len(headers)] = "0.0"
    last = write_table(sheet, 1, headers, rows, formats)
    fit(sheet, headers, rows)
    for column in date_columns:
        sheet.column_dimensions[get_column_letter(column)].width = 17
    for column in percent_columns:
        percent_scale(sheet, column, 2, last)
    sheet.freeze_panes = "C2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(last, 1)}"

    # --- subjects
    headers = ["Fan", "To‘g‘ri", "Noto‘g‘ri", "Javobsiz", "Jami javoblar", "O‘rtacha (%)"]
    rows = [
        [s["name"], s["correct"], s["incorrect"], s["unanswered"], s["total"], s["averagePercent"]]
        for s in report["subjects"]
    ]
    sheet = book.create_sheet("Fanlar")
    last = write_table(sheet, 1, headers, rows, {6: "0.0"})
    fit(sheet, headers, rows)
    percent_scale(sheet, 6, 2, last)

    # --- places
    groups = report["groups"]
    if groups:
        headers = [
            groups["label"],
            "O‘quvchilar",
            "O‘rtacha (%)",
            "Eng yuqori (%)",
            "Eng past (%)",
            "O‘rtacha ball",
            "A’lo (80%+)",
        ]
        rows = [
            [
                g["name"],
                g["count"],
                g["averagePercent"],
                g["maxPercent"],
                g["minPercent"],
                g["averageScore"],
                g["high"],
            ]
            for g in groups["rows"]
        ]
        sheet = book.create_sheet(groups["title"])
        last = write_table(sheet, 1, headers, rows, {3: "0.0", 4: "0.0", 5: "0.0", 6: "0.0"})
        fit(sheet, headers, rows)
        percent_scale(sheet, 3, 2, last)
        sheet.freeze_panes = "B2"

    # --- questions
    labels = sorted({option["label"] for q in report["questions"] for option in q["options"]})
    headers = [
        "Savol №",
        "Fan",
        "Qiyinlik",
        "To‘g‘ri javob",
        "To‘g‘ri",
        "Noto‘g‘ri",
        "Javobsiz",
        "To‘g‘ri (%)",
        *[f"{label} tanlagan" for label in labels],
    ]
    rows = []
    for q in report["questions"]:
        picked = {option["label"]: option["count"] for option in q["options"]}
        key = ", ".join(option["label"] for option in q["options"] if option["isCorrect"])
        rows.append(
            [
                q["number"],
                q["subjectName"],
                q["difficulty"],
                key,
                q["correct"],
                q["incorrect"],
                q["unanswered"],
                q["correctPercent"],
                *[picked.get(label) for label in labels],
            ]
        )
    sheet = book.create_sheet("Savollar")
    last = write_table(sheet, 1, headers, rows, {8: "0.0"})
    fit(sheet, headers, rows)
    percent_scale(sheet, 8, 2, last)
    sheet.freeze_panes = "B2"

    output = BytesIO()
    book.save(output)
    return output.getvalue()


# ------------------------------------------------------------------------------------ fonts


def _font_candidates() -> list[tuple[str, str]]:
    import reportlab

    bundled = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    own = getattr(settings, "REPORT_FONT", "")
    candidates = [(own, getattr(settings, "REPORT_FONT_BOLD", "") or own)] if own else []
    return candidates + [
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        ("/usr/share/fonts/TTF/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        (os.path.join(bundled, "Vera.ttf"), os.path.join(bundled, "VeraBd.ttf")),
    ]


@cache
def font_files() -> tuple[str, str]:
    for regular, bold in _font_candidates():
        if os.path.isfile(regular):
            return regular, bold if os.path.isfile(bold) else regular
    raise RuntimeError("PDF va rasm uchun shrift topilmadi.")


@cache
def _glyphs() -> frozenset[int]:
    from reportlab.pdfbase.ttfonts import TTFont

    return frozenset(TTFont("probe", font_files()[0]).face.charToGlyph)


# Uzbek has two spellings of its apostrophes; a font without the modifier letters gets the quotes.
_APOSTROPHES = {"ʻ": "‘", "ʼ": "’", "№": "#"}


def text(value) -> str:
    value = "" if value is None else str(value)
    glyphs = _glyphs()
    for char, plain in _APOSTROPHES.items():
        if char in value and ord(char) not in glyphs:
            value = value.replace(char, plain)
    return value


@cache
def _pdf_fonts() -> tuple[str, str]:
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular, bold = font_files()
    pdfmetrics.registerFont(TTFont("ReportSans", regular))
    pdfmetrics.registerFont(TTFont("ReportSans-Bold", bold))
    addMapping("ReportSans", 0, 0, "ReportSans")
    addMapping("ReportSans", 1, 0, "ReportSans-Bold")
    return "ReportSans", "ReportSans-Bold"


# -------------------------------------------------------------------------------------- PDF


def to_pdf(report: dict) -> bytes:
    from reportlab.graphics.shapes import Drawing, Line, Rect, String
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        KeepTogether,
        LongTable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    regular, bold = _pdf_fonts()
    exam = report["exam"]
    page = landscape(A4)
    margin = 12 * mm
    width = page[0] - 2 * margin
    color = colors.HexColor

    title_style = ParagraphStyle(
        "title", fontName=bold, fontSize=17, leading=21, textColor=color(BRAND)
    )
    sub_style = ParagraphStyle(
        "sub", fontName=regular, fontSize=9, leading=12, textColor=color(INK_SOFT), keepWithNext=1
    )
    h2 = ParagraphStyle(
        "h2",
        fontName=bold,
        fontSize=12,
        leading=15,
        spaceBefore=10,
        spaceAfter=6,
        textColor=color(INK),
        keepWithNext=1,  # a heading never stays alone at the bottom of a page
    )
    cell = ParagraphStyle("cell", fontName=regular, fontSize=7.5, leading=9)
    # A long subject name in a narrow column wraps instead of running into its neighbour.
    head_right = ParagraphStyle(
        "head", fontName=bold, fontSize=8, leading=9.5, alignment=2, textColor=color("#0b3a30")
    )

    def esc(value) -> str:
        return text(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def table(rows, widths, *, header_rows=1, align_right_from=1, long=False, extra=()):
        style = [
            ("FONT", (0, 0), (-1, -1), regular, 8),
            ("FONT", (0, 0), (-1, header_rows - 1), bold, 8),
            ("BACKGROUND", (0, 0), (-1, header_rows - 1), color(BRAND_SOFT)),
            ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), color("#0b3a30")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, color(LINE)),
            ("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            *extra,
        ]
        rows = [
            [cell_ if isinstance(cell_, Paragraph) else text(cell_) for cell_ in row]
            for row in rows
        ]
        kind = LongTable if long else Table
        return kind(
            rows, colWidths=widths, repeatRows=header_rows, style=TableStyle(style), hAlign="LEFT"
        )

    def band_cells(column, values):
        commands = []
        for index, value in enumerate(values, start=1):
            if value is None:
                continue
            band = "high" if value >= 80 else "mid" if value >= 50 else "growing"
            commands.append(
                ("BACKGROUND", (column, index), (column, index), color(BAND_SOFT[band]))
            )
            commands.append(
                ("TEXTCOLOR", (column, index), (column, index), color(BAND_COLORS[band]))
            )
        return commands

    story = [
        Paragraph(esc(exam["title"]) + " — natijalar", title_style),
        Paragraph(
            esc(
                f"{filters_text(report, with_exam=False)}  ·  {exam['questionCount']} ta savol, "
                f"{exam['durationMinutes']} daqiqa, maksimal ball {exam['maxScore']}  ·  "
                f"Tuzilgan vaqti: {when(report['generatedAt'])}"
            ),
            sub_style,
        ),
        Spacer(1, 8),
    ]

    # Summary next to the distribution chart.
    summary = table([("Ko‘rsatkich", "Qiymat"), *summary_rows(report)], [62 * mm, 38 * mm])
    chart_width, chart_height = width - 112 * mm, 62 * mm
    chart = Drawing(chart_width, chart_height)
    buckets = report["distribution"]
    top = max([item["count"] for item in buckets] + [1])
    plot_h = chart_height - 30
    slot = chart_width / len(buckets)
    chart.add(
        String(
            0,
            chart_height - 10,
            text("Natijalar taqsimoti (o‘quvchilar soni)"),
            fontName=bold,
            fontSize=9,
            fillColor=color(INK),
        )
    )
    chart.add(Line(0, 14, chart_width, 14, strokeColor=color(LINE), strokeWidth=0.6))
    for index, item in enumerate(buckets):
        bar_h = plot_h * item["count"] / top
        band = "high" if item["from"] >= 80 else "mid" if item["from"] >= 50 else "growing"
        x = index * slot + slot * 0.15
        chart.add(
            Rect(x, 14, slot * 0.7, bar_h, fillColor=color(BAND_COLORS[band]), strokeColor=None)
        )
        chart.add(
            String(
                x + slot * 0.35,
                18 + bar_h,
                str(item["count"]),
                fontName=bold,
                fontSize=7.5,
                textAnchor="middle",
            )
        )
        chart.add(
            String(
                x + slot * 0.35,
                4,
                f"{item['label']}%",
                fontName=regular,
                fontSize=7,
                textAnchor="middle",
                fillColor=color(INK_SOFT),
            )
        )
    story.append(
        Table(
            [[summary, chart]],
            colWidths=[108 * mm, chart_width + 4 * mm],
            style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)],
            hAlign="LEFT",
        )
    )

    # Bands and subjects side by side.
    bands = table(
        [
            ("Daraja", "Oraliq", "O‘quvchilar"),
            *[(b["label"], b["range"], b["count"]) for b in report["bands"]],
        ],
        [30 * mm, 24 * mm, 24 * mm],
    )
    subject_rows = [
        (s["name"], percent(s["averagePercent"]), s["correct"], s["incorrect"], s["unanswered"])
        for s in report["subjects"]
    ]
    subjects = table(
        [("Fan", "O‘rtacha", "To‘g‘ri", "Noto‘g‘ri", "Javobsiz"), *subject_rows],
        [44 * mm, 22 * mm, 20 * mm, 20 * mm, 20 * mm],
        extra=band_cells(1, [s["averagePercent"] for s in report["subjects"]]),
    )
    story.append(
        KeepTogether(
            [
                Paragraph("Darajalar va fanlar", h2),
                Table(
                    [[bands, subjects]],
                    colWidths=[84 * mm, 130 * mm],
                    style=[
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ],
                    hAlign="LEFT",
                ),
            ]
        )
    )

    groups = report["groups"]
    if groups and groups["rows"]:
        rows = [
            (
                Paragraph(esc(g["name"]), cell),
                g["count"],
                percent(g["averagePercent"]),
                percent(g["maxPercent"]),
                percent(g["minPercent"]),
                number(g["averageScore"]),
                g["high"],
            )
            for g in groups["rows"]
        ]
        story += [
            Paragraph(esc(f"{groups['title']} bo‘yicha"), h2),
            table(
                [
                    (
                        groups["label"],
                        "O‘quvchilar",
                        "O‘rtacha",
                        "Eng yuqori",
                        "Eng past",
                        "O‘rtacha ball",
                        "A’lo (80%+)",
                    ),
                    *rows,
                ],
                [width - 150 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 26 * mm, 26 * mm],
                long=True,
                extra=band_cells(2, [g["averagePercent"] for g in groups["rows"]]),
            ),
        ]

    questions = report["questions"]
    if questions:
        rows = []
        for q in questions:
            picks = "   ".join(
                f"{o['label']}{'*' if o['isCorrect'] else ''}: {o['count']}" for o in q["options"]
            )
            rows.append(
                (
                    q["number"],
                    q["subjectName"],
                    q["difficulty"] or "—",
                    percent(q["correctPercent"]),
                    q["correct"],
                    q["incorrect"],
                    q["unanswered"],
                    picks,
                )
            )
        story += [
            Paragraph("Savollar tahlili", h2),
            Paragraph(
                esc(
                    "To‘g‘ri javob * bilan belgilangan. Savollar imtihondagi asl raqami va "
                    "harflari bilan, hozirgi javob kaliti bo‘yicha."
                ),
                sub_style,
            ),
            Spacer(1, 4),
            table(
                [
                    (
                        "№",
                        "Fan",
                        "Qiyinlik",
                        "To‘g‘ri, %",
                        "To‘g‘ri",
                        "Noto‘g‘ri",
                        "Javobsiz",
                        "Variantlarni tanlaganlar",
                    ),
                    *rows,
                ],
                [12 * mm, 40 * mm, 22 * mm, 22 * mm, 18 * mm, 20 * mm, 20 * mm, width - 154 * mm],
                long=True,
                extra=[
                    ("ALIGN", (7, 0), (7, -1), "LEFT"),
                    ("ALIGN", (1, 0), (2, -1), "LEFT"),
                    *band_cells(3, [q["correctPercent"] for q in questions]),
                ],
            ),
        ]

    pupils = report["pupils"]
    if pupils:
        subject_columns = report["subjectColumns"]
        header = [
            "O‘rin",
            "F.I.Sh.",
            "Maktab",
            "Sinf",
            "To‘g‘ri",
            "Ball",
            "Foiz",
            *[Paragraph(esc(s["name"]), head_right) for s in subject_columns],
            Paragraph("Vaqt (daq.)", head_right),
        ]
        rows = [
            [
                p["rank"],
                Paragraph(esc(p["name"]), cell),
                Paragraph(esc(p["school"]), cell),
                Paragraph(esc(p["classroom"]), cell),
                f"{p['correct']}/{p['total']}",
                p["score"],
                percent(p["percent"]),
                *[percent(p["subjects"].get(s["code"])) for s in subject_columns],
                number(p["durationMinutes"]),
            ]
            for p in pupils
        ]
        fixed = 12 * mm + 16 * mm + 14 * mm + 16 * mm + 24 * mm * len(subject_columns) + 18 * mm
        rest = width - fixed
        widths = [
            12 * mm,
            rest * 0.42,
            rest * 0.38,
            rest * 0.20,
            16 * mm,
            14 * mm,
            16 * mm,
            *[24 * mm] * len(subject_columns),
            18 * mm,
        ]
        story += [
            Paragraph(esc(f"O‘quvchilar ({len(pupils)} ta)"), h2),
            table(
                [header, *rows],
                widths,
                long=True,
                align_right_from=4,
                extra=[
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    *band_cells(6, [p["percent"] for p in pupils]),
                ],
            ),
        ]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(regular, 7.5)
        canvas.setFillColor(color(INK_SOFT))
        canvas.drawString(margin, 7 * mm, text(f"{exam['title']} · {when(report['generatedAt'])}"))
        canvas.drawRightString(page[0] - margin, 7 * mm, f"{doc.page}-bet")
        canvas.restoreState()

    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=page,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=14 * mm,
        title=text(f"{exam['title']} — natijalar"),
        author="Bilimdon",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()


# -------------------------------------------------------------------------------------- PNG


def to_png(report: dict) -> bytes:
    """One picture to share in a chat: the main numbers, the charts and the top of the lists."""
    from PIL import Image, ImageDraw, ImageFont

    regular_path, bold_path = font_files()

    @cache
    def font(size: int, heavy: bool = False):
        return ImageFont.truetype(bold_path if heavy else regular_path, size)

    exam = report["exam"]
    summary = report["summary"]
    pupils = report["pupils"][:10]
    groups = (report["groups"] or {}).get("rows", [])[:10]
    width, pad = 1600, 48
    list_rows = max(len(pupils), len(groups), 1)
    subjects = report["subjects"][:6]
    # The right panel holds the three bands and the subjects; the charts row grows to fit them.
    panel_h = max(440, 76 + 3 * 62 + 58 + len(subjects) * 52 + 16)
    height = 180 + 170 + panel_h + 30 + 90 + list_rows * 44 + 80
    image = Image.new("RGB", (width, height), SURFACE)
    draw = ImageDraw.Draw(image)

    def fit(value: str, size: int, limit: float, heavy: bool = False) -> str:
        value = text(value)
        face = font(size, heavy)
        if face.getlength(value) <= limit:
            return value
        while value and face.getlength(value + "…") > limit:
            value = value[:-1]
        return value.rstrip() + "…"

    def card(box, fill="#ffffff"):
        draw.rounded_rectangle(box, radius=22, fill=fill, outline="#e2e9e6")

    # Header
    draw.rectangle((0, 0, width, 150), fill=BRAND)
    draw.text(
        (pad, 34),
        fit(f"{exam['title']} — natijalar", 40, width - 2 * pad, True),
        font=font(40, True),
        fill="#ffffff",
    )
    draw.text(
        (pad, 96),
        fit(
            f"{filters_text(report, with_exam=False)}  ·  {when(report['generatedAt'])}",
            22,
            width - 2 * pad,
        ),
        font=font(22),
        fill="#dbf5ea",
    )

    # Stat cards
    y = 180
    stats = [
        ("O‘quvchilar", number(summary.get("count", 0)), BRAND),
        ("O‘rtacha natija", percent(summary.get("averagePercent")), BRAND),
        ("Mediana", percent(summary.get("medianPercent")), "#5b6f69"),
        ("Eng yuqori", percent(summary.get("maxPercent")), BAND_COLORS["high"]),
        ("Eng past", percent(summary.get("minPercent")), BAND_COLORS["growing"]),
    ]
    gap = 20
    card_w = (width - 2 * pad - gap * (len(stats) - 1)) / len(stats)
    for index, (label, value, accent) in enumerate(stats):
        x = pad + index * (card_w + gap)
        card((x, y, x + card_w, y + 140))
        draw.rounded_rectangle((x, y, x + card_w, y + 8), radius=4, fill=accent)
        draw.text((x + 24, y + 30), text(value), font=font(46), fill=INK)
        draw.text((x + 24, y + 96), text(label), font=font(22), fill=INK_SOFT)

    # Distribution
    y += 170
    left_w = 900
    card((pad, y, pad + left_w, y + panel_h))
    draw.text((pad + 28, y + 24), text("Natijalar taqsimoti"), font=font(26, True), fill=INK)
    buckets = report["distribution"]
    top = max([item["count"] for item in buckets] + [1])
    plot_x, plot_y, plot_w, plot_h = pad + 28, y + 90, left_w - 56, panel_h - 160
    slot = plot_w / len(buckets)
    draw.line((plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h), fill=LINE, width=2)
    for index, item in enumerate(buckets):
        bar_h = plot_h * item["count"] / top
        band = "high" if item["from"] >= 80 else "mid" if item["from"] >= 50 else "growing"
        x0 = plot_x + index * slot + slot * 0.14
        x1 = x0 + slot * 0.72
        if bar_h:
            draw.rounded_rectangle(
                (x0, plot_y + plot_h - bar_h, x1, plot_y + plot_h), radius=6, fill=BAND_COLORS[band]
            )
        label = str(item["count"])
        draw.text(
            ((x0 + x1) / 2, plot_y + plot_h - bar_h - 8),
            label,
            font=font(20, True),
            fill=INK,
            anchor="ms",
        )
        draw.text(
            ((x0 + x1) / 2, plot_y + plot_h + 30),
            item["label"],
            font=font(18),
            fill=INK_SOFT,
            anchor="ms",
        )
    draw.text(
        (plot_x, y + panel_h - 30),
        text("Foiz oralig‘i bo‘yicha o‘quvchilar soni"),
        font=font(18),
        fill=INK_SOFT,
    )

    # Bands and subjects
    right_x = pad + left_w + 20
    right_w = width - pad - right_x
    card((right_x, y, right_x + right_w, y + panel_h))
    draw.text((right_x + 28, y + 24), text("Darajalar"), font=font(26, True), fill=INK)
    total = max(summary.get("count", 0), 1)
    by = y + 76
    bar_w = right_w - 56
    for band in report["bands"]:
        share = band["count"] / total
        draw.text(
            (right_x + 28, by), text(f"{band['label']} ({band['range']})"), font=font(20), fill=INK
        )
        draw.text(
            (right_x + 28 + bar_w, by),
            f"{band['count']}",
            font=font(20, True),
            fill=INK,
            anchor="ra",
        )
        draw.rounded_rectangle(
            (right_x + 28, by + 32, right_x + 28 + bar_w, by + 44), radius=6, fill="#e2e9e6"
        )
        if share:
            draw.rounded_rectangle(
                (right_x + 28, by + 32, right_x + 28 + max(bar_w * share, 12), by + 44),
                radius=6,
                fill=BAND_COLORS[band["code"]],
            )
        by += 62
    draw.text(
        (right_x + 28, by + 6), text("Fanlar bo‘yicha o‘rtacha"), font=font(26, True), fill=INK
    )
    by += 52
    for subject in subjects:
        value = subject["averagePercent"] or 0
        band = "high" if value >= 80 else "mid" if value >= 50 else "growing"
        draw.text((right_x + 28, by), fit(subject["name"], 20, bar_w - 90), font=font(20), fill=INK)
        draw.text(
            (right_x + 28 + bar_w, by),
            percent(subject["averagePercent"]),
            font=font(20, True),
            fill=INK,
            anchor="ra",
        )
        draw.rounded_rectangle(
            (right_x + 28, by + 30, right_x + 28 + bar_w, by + 40), radius=5, fill="#e2e9e6"
        )
        if value:
            draw.rounded_rectangle(
                (right_x + 28, by + 30, right_x + 28 + max(bar_w * value / 100, 10), by + 40),
                radius=5,
                fill=BAND_COLORS[band],
            )
        by += 52

    # Top pupils and places
    y += panel_h + 30
    list_h = 90 + list_rows * 44
    half = (width - 2 * pad - 20) / 2 if groups else width - 2 * pad
    card((pad, y, pad + half, y + list_h))
    draw.text((pad + 28, y + 24), text("Eng yaxshi natijalar"), font=font(26, True), fill=INK)
    for index, pupil in enumerate(pupils):
        ry = y + 80 + index * 44
        if index % 2 == 0:
            draw.rectangle((pad + 12, ry - 6, pad + half - 12, ry + 34), fill="#f7faf8")
        draw.text((pad + 28, ry), f"{pupil['rank']}.", font=font(20, True), fill=INK_SOFT)
        draw.text(
            (pad + 80, ry),
            fit(f"{pupil['name']} · {pupil['school']}, {pupil['classroom']}", 20, half - 260),
            font=font(20),
            fill=INK,
        )
        draw.text(
            (pad + half - 28, ry),
            f"{pupil['score']} ball · {percent(pupil['percent'])}",
            font=font(20, True),
            fill=BAND_COLORS[pupil["band"]],
            anchor="ra",
        )
    if not pupils:
        draw.text((pad + 28, y + 80), text("Natijalar yo‘q"), font=font(20), fill=INK_SOFT)
    if groups:
        gx = pad + half + 20
        card((gx, y, gx + half, y + list_h))
        draw.text(
            (gx + 28, y + 24),
            text(f"{report['groups']['title']} (o‘rtacha natija)"),
            font=font(26, True),
            fill=INK,
        )
        for index, group in enumerate(groups):
            ry = y + 80 + index * 44
            if index % 2 == 0:
                draw.rectangle((gx + 12, ry - 6, gx + half - 12, ry + 34), fill="#f7faf8")
            value = group["averagePercent"]
            band = "high" if value >= 80 else "mid" if value >= 50 else "growing"
            draw.text(
                (gx + 28, ry),
                fit(f"{index + 1}. {group['name']}", 20, half - 260),
                font=font(20),
                fill=INK,
            )
            draw.text(
                (gx + half - 28, ry),
                f"{group['count']} ta · {percent(value)}",
                font=font(20, True),
                fill=BAND_COLORS[band],
                anchor="ra",
            )

    draw.text(
        (pad, height - 44),
        text("Bilimdon · imtihon natijalari hisoboti"),
        font=font(18),
        fill=INK_SOFT,
    )
    output = BytesIO()
    image.save(output, "PNG", optimize=True)
    return output.getvalue()
