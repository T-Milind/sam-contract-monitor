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
    return styles


def _markdown_lite_to_html(text):
    """Gemini output is markdown-ish; convert the bits reportlab's Paragraph
    understands (bold, headers-as-bold) and escape the rest."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
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

    summary_data = [["#", "Title", "Agency", "Stage 1 Score"]]
    for i, c in enumerate(scored_contracts, 1):
        summary_data.append([str(i), c["title"][:60], c["agency"][:35], f"{c['stage1_score']:.1f}"])
    table = Table(summary_data, colWidths=[0.3 * inch, 3.4 * inch, 2.3 * inch, 1 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
    ]))
    story.append(table)
    story.append(PageBreak())

    for i, c in enumerate(scored_contracts, 1):
        story.append(Paragraph(f"{i}. {c['title']}", styles["ContractTitle"]))
        meta = (
            f"Agency: {c['agency']} &nbsp;|&nbsp; Type: {c['notice_type']} &nbsp;|&nbsp; "
            f"Stage 1 Score: {c['stage1_score']:.1f}/10 &mdash; {c['stage1_reason']}<br/>"
            f"Published: {c.get('publish_date', 'N/A')} &nbsp;|&nbsp; "
            f'<link href="{c["link"]}">{c["link"]}</link>'
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
