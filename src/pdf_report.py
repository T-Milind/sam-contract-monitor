"""Compiles Stage 2 capture-analysis reports into a single PDF."""
import os
import re
from datetime import datetime

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
)

from . import config


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", fontSize=18, leading=22, spaceAfter=14, textColor=colors.HexColor("#1a1a2e")))
    styles.add(ParagraphStyle(name="ContractTitle", fontSize=14, leading=18, spaceBefore=6, spaceAfter=8, textColor=colors.HexColor("#16213e")))
    styles.add(ParagraphStyle(name="Meta", fontSize=9, leading=13, textColor=colors.HexColor("#555555")))
    styles.add(ParagraphStyle(name="Body", fontSize=10, leading=14, spaceAfter=6))
    styles.add(ParagraphStyle(name="TableCell", fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="TableHeader", fontSize=9, leading=11, textColor=colors.white))
    styles.add(ParagraphStyle(name="TableCellLink", fontSize=9, leading=11, textColor=colors.HexColor("#1a56db")))
    return styles


def _esc(text):
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _markdown_lite_to_html(text):
    """Gemini output is markdown-ish; convert the bits reportlab's Paragraph
    understands (bold, headers-as-bold) and escape the rest."""
    text = _esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"^#{1,6}\s*(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    return text


def build_pdf(scored_contracts, output_path):
    """scored_contracts: list of dicts with keys title, agency, notice_type,
    link, stage1_score, stage1_reason, stage2_report, publish_date."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=LETTER,
                             topMargin=0.75 * inch, bottomMargin=0.75 * inch,
                             leftMargin=0.75 * inch, rightMargin=0.75 * inch)
    styles = _styles()
    story = []

    run_date = datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph("SAM.gov IT Contract Monitor", styles["ReportTitle"]))
    story.append(Paragraph(f"Run date: {run_date} &nbsp;&nbsp;|&nbsp;&nbsp; {len(scored_contracts)} opportunity(ies) cleared Stage 1 (score ≥ {config.STAGE1_THRESHOLD})", styles["Meta"]))
    story.append(Spacer(1, 16))

    header = [Paragraph(h, styles["TableHeader"]) for h in ["#", "Title", "Agency", "Stage 1 Score"]]
    summary_data = [header]
    for i, c in enumerate(scored_contracts, 1):
        title_cell = Paragraph(f'<link href="{c["link"]}"><u>{_esc(c["title"])}</u></link>', styles["TableCellLink"])
        agency_cell = Paragraph(_esc(c["agency"]), styles["TableCell"])
        score_cell = Paragraph(f"{c['stage1_score']:.1f}", styles["TableCell"])
        num_cell = Paragraph(str(i), styles["TableCell"])
        summary_data.append([num_cell, title_cell, agency_cell, score_cell])
    table = Table(summary_data, colWidths=[0.3 * inch, 3.4 * inch, 2.3 * inch, 1 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
    ]))
    story.append(table)
    story.append(PageBreak())

    for i, c in enumerate(scored_contracts, 1):
        story.append(Paragraph(f'{i}. <link href="{c["link"]}"><u>{_esc(c["title"])}</u></link>', styles["ContractTitle"]))
        meta = (
            f"Agency: {_esc(c['agency'])} &nbsp;|&nbsp; Type: {_esc(c['notice_type'])} &nbsp;|&nbsp; "
            f"Stage 1 Score: {c['stage1_score']:.1f}/10 &mdash; {_esc(c['stage1_reason'])}<br/>"
            f"Published: {_esc(c.get('publish_date', 'N/A'))} &nbsp;|&nbsp; "
            f'<link href="{c["link"]}">{_esc(c["link"])}</link>'
        )
        story.append(Paragraph(meta, styles["Meta"]))
        story.append(Spacer(1, 10))

        for para in c["stage2_report"].split("\n\n"):
            para = para.strip()
            if not para:
                continue
            story.append(Paragraph(_markdown_lite_to_html(para), styles["Body"]))

        if i < len(scored_contracts):
            story.append(PageBreak())

    doc.build(story)
    return output_path
