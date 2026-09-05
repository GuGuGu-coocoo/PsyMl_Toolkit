"""Render the Chinese README section and researcher guide into release PDFs.

Requires reportlab and an embeddable TrueType font with Chinese/Latin/math glyphs.
Example: uv run --with reportlab python tools/build_release_pdfs.py --font /path/font.ttf
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
BLUE = colors.HexColor("#334a88")
WIDTH = 499
# Plain mathematical equivalents avoid dependence on a network LaTeX renderer.
FORMULAS = [
    "p(y = 1 | x) = 1 / {1 + exp[−(b + βᵀx)]}",
    "目标 = 拟合损失 + λ × 惩罚<br/>L₁ = Σⱼ |βⱼ|；L₂ = Σⱼ βⱼ²",
    "Precision = TP / (TP + FP)<br/>Recall = TP / (TP + FN)<br/>F₁ = 2TP / (2TP + FP + FN)",
    "MAE = (1/n) Σᵢ |yᵢ − ŷᵢ|<br/>RMSE = √[(1/n) Σᵢ (yᵢ − ŷᵢ)²]",
    "R² = 1 − [Σᵢ (yᵢ − ŷᵢ)²] / [Σᵢ (yᵢ − ȳ)²]",
]


def supported_glyphs(text: str) -> str:
    for old, new in {"📖": "", "ȳ": "y_mean", "ᵀ": "<super>T</super>",
                     "ᵢ": "<sub>i</sub>", "ⱼ": "<sub>j</sub>",
                     "–": "-", "—": "-", "‑": "-"}.items():
        text = text.replace(old, new)
    return text


def inline(text: str, base: str) -> str:
    text = supported_glyphs(html.escape(text))

    def link(match: re.Match) -> str:
        label, target = match.groups()
        target = html.unescape(target).strip("<>")
        if target.startswith("#"):
            return label
        url = urljoin(base, target)
        return f'<link href="{html.escape(url, quote=True)}" color="#334a88">{label}</link>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"`([^`]+)`", r'<font color="#334a88">\1</font>', text)


def render(source: Path, text: str, target: Path, title: str) -> None:
    body = ParagraphStyle(
        "body", fontName="PsyMLCJK", fontSize=10, leading=16,
        wordWrap="CJK", spaceAfter=7, alignment=TA_LEFT,
    )
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=13, spaceAfter=0)
    heading = {
        n: ParagraphStyle(
            f"h{n}", parent=body, fontSize=22 if n == 1 else 15 if n == 2 else 12,
            leading=28 if n == 1 else 21 if n == 2 else 18,
            textColor=BLUE, spaceBefore=14, spaceAfter=9, keepWithNext=True,
        ) for n in range(1, 7)
    }
    base = "https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/blob/v0.1.0/"
    base += source.relative_to(ROOT).as_posix()
    story = [Paragraph(title, heading[1]), Paragraph("PsyML Toolkit · v0.1.0", body)]
    story.append(Paragraph(
        "本文可离线阅读。蓝色链接指向 v0.1.0 的仓库文件或外部资料，需要联网。"
        "命令请从解压后的项目根目录执行。", small,
    ))
    story.append(Spacer(1, 12))
    lines = text.splitlines()
    i = 0
    formula_index = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith(("<a ", "<p")) or line == "</p>":
            continue
        if line.startswith("$$"):
            while i < len(lines) and lines[i].strip() != "$$":
                i += 1
            i += 1
            equation = Paragraph(supported_glyphs(FORMULAS[formula_index]), body)
            formula_index += 1
            story.extend([Spacer(1, 5), equation, Spacer(1, 5)])
        elif line.startswith("```"):
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(html.escape(lines[i]))
                i += 1
            i += 1
            block = Table([[Paragraph("<br/>".join(code), small)]], colWidths=[WIDTH])
            block.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef1f8")),
                ("BOX", (0, 0), (-1, -1), .4, colors.HexColor("#d5dced")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.extend([block, Spacer(1, 9)])
        elif line.startswith("!["):
            match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            if match:
                caption, raw = match.groups()
                path = source.parent / raw
                width, height = ImageReader(str(path)).getSize()
                image = Image(str(path), width=WIDTH, height=WIDTH * height / width)
                story.append(KeepTogether([image, Paragraph(caption, small), Spacer(1, 10)]))
        elif line.startswith("|"):
            rows = [line]
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            cells = []
            for row in rows:
                if re.fullmatch(r"[| :\-]+", row):
                    continue
                cells.append([Paragraph(inline(c.strip(), base), small)
                              for c in row.strip("|").split("|")])
            count = len(cells[0])
            widths = [175, 324] if count == 2 else [160, 165, 174]
            table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce4f4")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fc")]),
                ("LINEBELOW", (0, 0), (-1, -1), .3, colors.HexColor("#dce2ec")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.extend([table, Spacer(1, 10)])
        elif line.startswith("#"):
            level = min(len(line) - len(line.lstrip("#")), 6)
            story.append(Paragraph(inline(line.lstrip("# "), base), heading[level]))
        else:
            story.append(Paragraph(inline(line, base), body))

    def page(canvas, doc):
        canvas.saveState()
        canvas.setFont("PsyMLCJK", 8)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(48, 818, "PsyML Toolkit v0.1.0 · " + title)
        canvas.drawRightString(547, 25, str(doc.page))
        canvas.restoreState()

    target.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(
        str(target), pagesize=(595, 842), leftMargin=48, rightMargin=48,
        topMargin=45, bottomMargin=42, title=title, author="PsyML Toolkit",
    ).build(story, onFirstPage=page, onLaterPages=page)
    assert formula_index == (5 if "RESEARCHER" in source.name else 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True)
    args = parser.parse_args()
    pdfmetrics.registerFont(TTFont("PsyMLCJK", str(args.font)))
    pdfmetrics.registerFontFamily("PsyMLCJK", normal="PsyMLCJK", bold="PsyMLCJK")
    readme = ROOT / "README.md"
    guide = ROOT / "docs/RESEARCHER_GUIDE_ZH.md"
    chinese = readme.read_text(encoding="utf-8").split('<a id="chinese"></a>')[1]
    chinese = chinese.split('<a id="english"></a>')[0].replace("## 中文", "", 1)
    render(readme, chinese, ROOT / "output/pdf/README_ZH.pdf", "中文版使用说明")
    guide_text = guide.read_text(encoding="utf-8").split("\n", 1)[1]
    render(guide, guide_text, ROOT / "output/pdf/RESEARCHER_GUIDE_ZH.pdf", "模型、指标、结果与术语")
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [readme, guide, *sorted((ROOT / "docs/images/zh").glob("*.png"))]}
    (ROOT / "output/pdf/sources.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("PSYML_RELEASE_PDFS_OK")


if __name__ == "__main__":
    main()
