# backend/app/services/reports.py
from __future__ import annotations

from io import BytesIO
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# --- Fonts (Cyrillic support) -------------------------------------------------

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping  # ⬅️ важно

def _register_fonts() -> str | None:
    roots = [
        Path(__file__).resolve().parent.parent / "assets" / "fonts",
        Path.home() / "Library" / "Fonts",
        Path("/Library/Fonts"),
    ]
    normal = next((r / "DejaVuSans.ttf" for r in roots if (r / "DejaVuSans.ttf").exists()), None)
    bold   = next((r / "DejaVuSans-Bold.ttf" for r in roots if (r / "DejaVuSans-Bold.ttf").exists()), None)

    if normal:
        pdfmetrics.registerFont(TTFont("DejaVuSans", str(normal)))
    if bold:
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(bold)))
    if normal and bold:
        addMapping("DejaVuSans", 0, 0, "DejaVuSans")
        addMapping("DejaVuSans", 1, 0, "DejaVuSans-Bold")
        addMapping("DejaVuSans", 0, 1, "DejaVuSans")
        addMapping("DejaVuSans", 1, 1, "DejaVuSans-Bold")
        return "DejaVuSans"
    return None

FONT_FAMILY = _register_fonts()

FONT_NAME = FONT_FAMILY or "Helvetica"
# --- Formatting helpers -------------------------------------------------------

def _fmt_pct(x) -> str:
    try:
        return f"{float(x):.2f}%"
    except Exception:
        return "—"

def _fmt_num(x) -> str:
    try:
        return f"{float(x):,.0f}".replace(",", " ")
    except Exception:
        return "—"

# --- PDF builder --------------------------------------------------------------

def build_pdf(
    baseline: Dict[str, Any] | None,
    scenario: Dict[str, Any] | None,
    advice: Dict[str, Any] | None,
    horizon_days: int | None = None,
) -> bytes:
    """
    Собирает PDF-бриф CFO. Возвращает байты PDF.
    baseline: ответ /forecast
    scenario: ответ /scenario
    advice:   ответ /advice
    """
    baseline = baseline or {}
    scenario = scenario or {}
    advice = advice or {}

    styles = getSampleStyleSheet()

    # База
    styles.add(ParagraphStyle(
        name="P",
        parent=styles["BodyText"],
        fontName=(FONT_FAMILY or styles["BodyText"].fontName),
        fontSize=10,
        leading=14,
    ))

    # Заголовки (без -Bold!)
    styles.add(ParagraphStyle(
        name="H1",
        parent=styles["Heading1"],
        fontName=(FONT_FAMILY or styles["Heading1"].fontName),
        fontSize=16,
        leading=20,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="H2",
        parent=styles["Heading2"],
        fontName=(FONT_FAMILY or styles["Heading2"].fontName),
        fontSize=12,
        leading=16,
        spaceAfter=6,
    ))

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
    )
    story: List[Any] = []

    # Header
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph("Liquidity Assistant — Бриф CFO", styles["H1"]))
    story.append(Paragraph(f"Дата формирования: {now}", styles["P"]))
    story.append(Spacer(1, 8))

    # Прогноз и метрики
    m1 = baseline.get("metrics") or {}
    m2 = scenario.get("metrics") or {}
    rows = [
        ["Горизонт", str(horizon_days or "(не задан)")],
        ["sMAPE (baseline)", _fmt_pct(m1.get("smape"))],
        ["Сценарий", scenario.get("scenario", "baseline")],
        ["Минимальный прогнозный баланс", _fmt_num(scenario.get("min_cash"))],
        ["sMAPE (scenario)", _fmt_pct(m2.get("smape"))],
    ]
    tbl = Table(rows, colWidths=[220, 260])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), FONT_NAME), 
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("Прогноз и метрики", styles["H2"]))
    story.append(tbl)
    story.append(Spacer(1, 12))

    # Рекомендации
    story.append(Paragraph("Рекомендации", styles["H2"]))
    advice_text = advice.get("advice_text") or "Совет не сформирован."
    story.append(Paragraph(advice_text.replace("\n", "<br/>"), styles["P"]))
    story.append(Spacer(1, 6))

    actions = advice.get("actions") or []
    if actions:
        rows = [["Действие", "Сумма", "Обоснование"]]
        for a in actions:
            rows.append([
                a.get("title", "—"),
                _fmt_num(a.get("amount")),
                a.get("rationale", ""),
            ])
        tbl2 = Table(rows, colWidths=[200, 100, 180], repeatRows=1)
        tbl2.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), FONT_NAME), 
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(tbl2)

    # Build PDF
    doc.build(story)
    return buf.getvalue()
