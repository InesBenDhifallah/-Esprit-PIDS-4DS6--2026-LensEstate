from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import re

NAVY = HexColor("#1a3c5e")
GOLD = HexColor("#f59e0b")
LIGHT = HexColor("#f8fafc")
GRAY = HexColor("#64748b")
WHITE = HexColor("#ffffff")


def parse_markdown_table(bloc):
    rows = []
    for line in bloc:
        line = line.strip()
        if not line or set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    return rows


def generer_pdf(texte_markdown: str, output_path: str = "rapport.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    style_h1 = ParagraphStyle(
        "h1",
        fontSize=18,
        textColor=WHITE,
        backColor=NAVY,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        leading=26,
    )
    style_h2 = ParagraphStyle(
        "h2",
        fontSize=13,
        textColor=NAVY,
        spaceAfter=4,
        spaceBefore=14,
        fontName="Helvetica-Bold",
    )
    style_body = ParagraphStyle(
        "body",
        fontSize=10,
        textColor=HexColor("#1e293b"),
        spaceAfter=4,
        fontName="Helvetica",
        leading=16,
    )
    style_sub = ParagraphStyle(
        "sub",
        fontSize=8,
        textColor=GRAY,
        alignment=TA_CENTER,
        fontName="Helvetica-Oblique",
    )

    story = []
    story.append(Paragraph("RAPPORT DE BENCHMARKING IMMOBILIER", style_h1))
    story.append(Paragraph("Analyse generee par LensEstate AI - Periode 2025/2026", style_sub))
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD))
    story.append(Spacer(1, 0.3 * cm))

    lines = texte_markdown.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("# "):
            i += 1
            continue
        if line.startswith("## "):
            text = line.lstrip("#").strip()
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#e2e8f0")))
            story.append(Paragraph(text, style_h2))
        elif line.startswith("|"):
            bloc = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                bloc.append(lines[i])
                i += 1
            rows = parse_markdown_table(bloc)
            if rows:
                col_count = len(rows[0])
                col_width = (A4[0] - 4 * cm) / col_count
                table = Table(rows, colWidths=[col_width] * col_count)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
                            ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#e2e8f0")),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 0.3 * cm))
            continue
        elif line == "":
            story.append(Spacer(1, 0.2 * cm))
        else:
            line = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line)
            line = re.sub(r"\*(.*?)\*", r"<i>\1</i>", line)
            line = line.lstrip("- ").lstrip("* ")
            story.append(Paragraph(line, style_body))

        i += 1

    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("LensEstate - Smart Investment Solutions - Tunisie", style_sub))

    doc.build(story)
    return output_path
