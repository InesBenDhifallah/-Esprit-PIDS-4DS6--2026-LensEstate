import io
import os
import re

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

NAVY  = HexColor("#1a3c5e")
GOLD  = HexColor("#f59e0b")
LIGHT = HexColor("#f8fafc")
GRAY  = HexColor("#64748b")
WHITE = HexColor("#ffffff")

# Police arabe
_FONT_DIR = os.path.dirname(os.path.abspath(__file__))
_CAIRO_PATH = os.path.join(_FONT_DIR, "Amiri-Regular.ttf")
pdfmetrics.registerFont(TTFont("Cairo", _CAIRO_PATH))


def _is_arabic_text(text: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', text))


def fix_arabic(text: str) -> str:
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def parse_markdown_table(bloc):
    rows = []
    for line in bloc:
        line = line.strip()
        if not line or set(line.replace("|","").replace("-","").replace(":","").strip()) == set():
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    return rows


def generer_pdf(texte_markdown: str, output_path="rapport.pdf"):
    """output_path: chemin fichier (str) ou tampon binaire (ex. io.BytesIO) pour ReportLab."""
    
    is_arabic = _is_arabic_text(texte_markdown)
    font_name = "Cairo" if is_arabic else "Helvetica"
    font_bold = "Cairo" if is_arabic else "Helvetica-Bold"
    font_italic = "Cairo" if is_arabic else "Helvetica-Oblique"
    align_body = TA_RIGHT if is_arabic else TA_LEFT

    doc = SimpleDocTemplate(output_path, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)

    style_h1 = ParagraphStyle("h1", fontSize=18, textColor=WHITE,
        backColor=NAVY, spaceAfter=6, alignment=TA_CENTER,
        fontName=font_bold, leading=26)
    style_h2 = ParagraphStyle("h2", fontSize=13, textColor=NAVY,
        spaceAfter=4, spaceBefore=14, fontName=font_bold,
        alignment=align_body,
        wordWrap='RTL' if is_arabic else 'LTR')
    style_body = ParagraphStyle("body", fontSize=10,
        textColor=HexColor("#1e293b"), spaceAfter=4,
        fontName=font_name, leading=16, alignment=align_body,
        wordWrap='RTL' if is_arabic else 'LTR')
    style_sub = ParagraphStyle("sub", fontSize=8, textColor=GRAY,
        alignment=TA_CENTER, fontName=font_italic)
    

    story = []
    
    if is_arabic:
        title_text = fix_arabic("تقرير مقارنة عقارية")
    else:
        title_text = "RAPPORT DE BENCHMARKING IMMOBILIER"
    
    story.append(Paragraph(title_text, style_h1))
    story.append(Paragraph("Analyse generee par LensEstate AI - Periode 2025/2026", style_sub))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD))
    story.append(Spacer(1, 0.3*cm))

    lines = texte_markdown.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("# "):
            i += 1
            continue

        elif line.startswith("## "):
            text = line.lstrip("#").strip()
            if is_arabic:
                text = fix_arabic(text)
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#e2e8f0")))
            story.append(Paragraph(text, style_h2))

        elif line.startswith("|"):
            bloc = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                bloc.append(lines[i])
                i += 1
            rows = parse_markdown_table(bloc)
            if rows:
                if is_arabic:
                    rows = [[fix_arabic(cell) for cell in row] for row in rows]
                col_count = len(rows[0])
                col_width = (A4[0] - 4*cm) / col_count
                table = Table(rows, colWidths=[col_width]*col_count)
                table.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (-1,0), NAVY),
                    ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
                    ("FONTNAME",      (0,0), (-1,0), font_bold),
                    ("FONTSIZE",      (0,0), (-1,-1), 9),
                    ("ALIGN",         (0,0), (-1,-1), "RIGHT" if is_arabic else "LEFT"),
                    ("FONTNAME",      (0,1), (-1,-1), font_name),
                    ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT]),
                    ("GRID",          (0,0), (-1,-1), 0.3, HexColor("#e2e8f0")),
                    ("TOPPADDING",    (0,0), (-1,-1), 6),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                    ("LEFTPADDING",   (0,0), (-1,-1), 8),
                ]))
                story.append(table)
                story.append(Spacer(1, 0.3*cm))
            continue

        elif line == "":
            story.append(Spacer(1, 0.2*cm))

        else:
            line = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line)
            line = re.sub(r"\*(.*?)\*",     r"<i>\1</i>", line)
            line = line.lstrip("- ").lstrip("* ")
            if is_arabic:
                line = fix_arabic(line)
            story.append(Paragraph(line, style_body))

        i += 1

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "LensEstate - Smart Investment Solutions - Tunisie",
        style_sub))

    doc.build(story)
    return output_path