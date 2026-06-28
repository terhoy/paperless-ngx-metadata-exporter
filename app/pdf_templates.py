from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak

ACCENT = colors.HexColor("#123E73")
BORDER = colors.HexColor("#C8D2E0")
LIGHT = colors.HexColor("#F4F7FB")
GRID = colors.HexColor("#D8DEE8")

# Label presets are defined in millimetres.
# Avery L4745REV-25 / software code L4745:
# A4 sheet, 8 labels per sheet, 2 columns x 4 rows, each label 96 x 63.5 mm.
# Margins are derived from A4 geometry and should be printer-tested at 100 % scaling.
LABEL_PRESETS: dict[str, dict[str, float | int | str]] = {
    "avery_l4745rev_25": {
        "name": "Avery L4745REV-25 / L4745",
        "description": "Avtagbare etiketter 96 x 63.5 mm, 8 per A4-ark",
        "removable": True,
        "label_width_mm": 96.0,
        "label_height_mm": 63.5,
        "columns": 2,
        "rows": 4,
        "margin_left_mm": 9.0,
        "margin_top_mm": 21.5,
        "gap_x_mm": 0.0,
        "gap_y_mm": 0.0,
    },
    "generic_99x68": {
        "name": "Generisk 99 x 68 mm",
        "description": "Stor testetikett 99 x 68 mm, 6 per A4-ark",
        "removable": False,
        "label_width_mm": 99.0,
        "label_height_mm": 68.0,
        "columns": 2,
        "rows": 3,
        "margin_left_mm": 4.0,
        "margin_top_mm": 30.0,
        "gap_x_mm": 4.0,
        "gap_y_mm": 5.0,
    },
}


def label_presets() -> dict[str, dict[str, float | int | str]]:
    return LABEL_PRESETS


def _safe(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _date_sort_key(row: dict[str, Any]) -> str:
    return _safe(row.get("created") or row.get("added"))


def _dates(rows: list[dict[str, Any]]) -> tuple[str, str]:
    values = sorted([_date_sort_key(r) for r in rows if _date_sort_key(r)])
    if not values:
        return "", ""
    return values[0], values[-1]


def _summary(rows: list[dict[str, Any]], case_id: str, case_title: str, folder: str) -> dict[str, str]:
    period_from, period_to = _dates(rows)
    return {
        "case_id": case_id or "Uten saks-ID",
        "case_title": case_title or "Uten sakstittel",
        "folder": folder or "1 av 1",
        "period": f"{period_from} - {period_to}" if period_from and period_to else "",
        "count": str(len(rows)),
        "generated": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }


def _footer(canv: canvas.Canvas, doc) -> None:
    canv.saveState()
    canv.setFont("Helvetica", 8)
    canv.setFillColor(colors.HexColor("#666666"))
    canv.drawString(16 * mm, 10 * mm, "Generert fra Paperless-ngx Metadata Exporter")
    canv.drawRightString(A4[0] - 16 * mm, 10 * mm, f"Side {doc.page}")
    canv.restoreState()


def make_content_sheet_pdf(
    rows: list[dict[str, Any]],
    case_id: str = "",
    case_title: str = "",
    description: str = "",
    folder: str = "1 av 1",
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("ArchiveTitle", parent=styles["Title"], fontSize=18, leading=22, textColor=ACCENT, spaceAfter=8))
    styles.add(ParagraphStyle("ArchiveHeading", parent=styles["Heading2"], fontSize=11, leading=14, textColor=ACCENT, spaceBefore=8, spaceAfter=5))
    styles.add(ParagraphStyle("CellSmall", parent=styles["BodyText"], fontSize=7.8, leading=9.8))
    styles.add(ParagraphStyle("BodySmall", parent=styles["BodyText"], fontSize=9, leading=12))

    rows = sorted(rows, key=_date_sort_key)
    summary = _summary(rows, case_id, case_title, folder)

    story = []
    story.append(Paragraph("ARKIVINDEKS FOR SAKSMAPPE", styles["ArchiveTitle"]))
    story.append(Paragraph("Innholdsark for fysisk mappe / forside i arkivmappe", styles["BodySmall"]))
    story.append(Spacer(1, 5 * mm))

    meta_table = Table([
        ["Saks-ID", summary["case_id"], "Mappe", summary["folder"]],
        ["Sakstittel", summary["case_title"], "Dokumenter", summary["count"]],
        ["Periode", summary["period"], "Generert", summary["generated"]],
        ["Kilde", "Paperless-ngx metadata", "Sortering", "Dokumentdato stigende"],
    ], colWidths=[28 * mm, 78 * mm, 28 * mm, 44 * mm])
    meta_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8.5),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 8.5),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("OMFANG OG INNHOLD", styles["ArchiveHeading"]))
    story.append(Paragraph(description or "Innholdsarket er generert fra metadata i Paperless-ngx. Kontroller at alle relevante dokumenter er tatt med før fysisk arkivering.", styles["BodySmall"]))

    story.append(Paragraph("INNHOLDSLISTE", styles["ArchiveHeading"]))
    table_data: list[list[Any]] = [["Nr", "Dato", "Dokumenttittel", "Type", "Korrespondent"]]
    for idx, row in enumerate(rows, start=1):
        table_data.append([
            str(idx),
            _safe(row.get("created")),
            Paragraph(_safe(row.get("title")), styles["CellSmall"]),
            _safe(row.get("document_type")),
            _safe(row.get("correspondent")),
        ])

    doc_table = Table(table_data, colWidths=[10 * mm, 22 * mm, 82 * mm, 28 * mm, 36 * mm], repeatRows=1)
    doc_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFD")]),
    ]))
    story.append(doc_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("KONTROLLINFORMASJON", styles["ArchiveHeading"]))
    control_table = Table([
        ["Merknad", "Kontroller at metadata, saks-ID og dokumentutvalg stemmer før fysisk arkivering."],
        ["Kontrollert av", "________________________________        Dato: ________________"],
    ], colWidths=[35 * mm, 143 * mm])
    control_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.4),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8.4),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, GRID),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(control_table)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _draw_archive_label(c: canvas.Canvas, x: float, y: float, w: float, h: float, summary: dict[str, str]) -> None:
    c.setStrokeColor(colors.HexColor("#9AA8BA"))
    c.setLineWidth(0.5)
    c.roundRect(x, y, w, h, 3 * mm, stroke=1, fill=0)
    pad = 5 * mm
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x + pad, y + h - 10 * mm, summary["case_id"][:34])
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x + pad, y + h - 18 * mm, summary["case_title"][:46])
    c.setStrokeColor(colors.HexColor("#D5DCE6"))
    c.line(x + pad, y + h - 22 * mm, x + w - pad, y + h - 22 * mm)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8.3)
    lines = [
        "Type: Prosjektdokumentasjon",
        f"Periode: {summary['period']}",
        f"Dokumenter: {summary['count']}",
        f"Mappe: {summary['folder']}",
        "Innhold: Avtaler / tegninger / korrespondanse",
    ]
    ty = y + h - 29 * mm
    for line in lines:
        c.drawString(x + pad, ty, line[:62])
        ty -= 5 * mm
    c.setFont("Helvetica", 6.6)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(x + pad, y + 5 * mm, "Generert fra Paperless-ngx Metadata Exporter")


def _draw_spine_label(c: canvas.Canvas, x: float, y: float, w: float, h: float, summary: dict[str, str]) -> None:
    c.setStrokeColor(colors.HexColor("#9AA8BA"))
    c.roundRect(x, y, w, h, 2 * mm, stroke=1, fill=0)
    c.saveState()
    c.translate(x + w / 2, y + h / 2)
    c.rotate(90)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(0, 8 * mm, summary["case_id"][:28])
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(0, 0, summary["case_title"][:32])
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawCentredString(0, -8 * mm, f"{summary['period']}   MAPPE {summary['folder']}")
    c.restoreState()



def make_label_sheet_pdf(
    rows: list[dict[str, Any]],
    case_id: str = "",
    case_title: str = "",
    folder: str = "1 av 1",
    preset_name: str = "avery_l4745rev_25",
    x_offset_mm: float = 0.0,
    y_offset_mm: float = 0.0,
) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    summary = _summary(rows, case_id, case_title, folder)
    preset = LABEL_PRESETS.get(preset_name, LABEL_PRESETS["avery_l4745rev_25"])

    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(ACCENT)
    c.drawString(15 * mm, H - 11 * mm, "Etikettark A4")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(
        15 * mm,
        H - 16 * mm,
        f"Mal: {preset['description']}. Skriv ut i 100 %, ikke tilpass til side.",
    )

    label_w = float(preset["label_width_mm"]) * mm
    label_h = float(preset["label_height_mm"]) * mm
    gap_x = float(preset["gap_x_mm"]) * mm
    gap_y = float(preset["gap_y_mm"]) * mm
    left = (float(preset["margin_left_mm"]) + x_offset_mm) * mm
    top = H - (float(preset["margin_top_mm"]) + y_offset_mm) * mm
    rows_count = int(preset["rows"])
    cols_count = int(preset["columns"])

    for row in range(rows_count):
        for col in range(cols_count):
            x = left + col * (label_w + gap_x)
            y = top - (row + 1) * label_h - row * gap_y
            _draw_archive_label(c, x, y, label_w, label_h, summary)

    c.showPage()
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(ACCENT)
    c.drawString(15 * mm, H - 15 * mm, "Rygg-/sideetiketter A4")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(15 * mm, H - 20 * mm, "Smal etikett for mappe eller arkivboks. Mål ca. 38 x 192 mm.")

    spine_w = 38 * mm
    spine_h = 192 * mm
    gap = 5 * mm
    x0 = (W - (2 * spine_w + gap)) / 2
    y0 = 45 * mm
    for i in range(2):
        _draw_spine_label(c, x0 + i * (spine_w + gap), y0, spine_w, spine_h, summary)
    c.save()
    return buffer.getvalue()


def make_combined_archive_pdf(rows: list[dict[str, Any]], case_id: str = "", case_title: str = "", description: str = "", folder: str = "1 av 1") -> bytes:
    from pypdf import PdfReader, PdfWriter

    content_pdf = make_content_sheet_pdf(rows, case_id=case_id, case_title=case_title, description=description, folder=folder)
    label_pdf = make_label_sheet_pdf(rows, case_id=case_id, case_title=case_title, folder=folder)

    writer = PdfWriter()
    for pdf_bytes in (content_pdf, label_pdf):
        reader = PdfReader(BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    out = BytesIO()
    writer.write(out)
    return out.getvalue()
