#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disable-error-code="import-untyped,no-untyped-def"
"""Python module for generating a PDF containing all license texts that can be
found under ./license_texts/"""

import argparse
import csv
import html
import re
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle as PS
from reportlab.lib.units import cm, inch
from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer
from reportlab.platypus.doctemplate import PageTemplate
from reportlab.platypus.frames import Frame
from reportlab.platypus.tableofcontents import TableOfContents
from svglib.svglib import svg2rlg


def tokenize(input_s: str) -> list[str]:
    ret_list = []
    stack = ""
    for token in re.split(r"(\(|\)|\s)", input_s):
        # the whitespaces
        if not token.strip():
            continue
        if token in ("(", ")", "AND", "OR"):
            if stack:
                ret_list.append(stack.strip())
                stack = ""
            ret_list.append(token)
        else:
            stack += " " + token
    if stack:
        ret_list.append(stack.strip())
    return ret_list


def test_tokenize() -> None:
    assert tokenize("MIT AND BSD-3-Clause AND Zlib") == [
        "MIT",
        "AND",
        "BSD-3-Clause",
        "AND",
        "Zlib",
    ]
    assert tokenize("BSD-3-Clause") == ["BSD-3-Clause"]
    assert tokenize(
        "(DocumentRef-spdx-tool-1.2:LicenseRef-MIT-Style-2 OR (Apache-2.0 AND PostgreSQL OR OpenSSL)) AND (BSD-3-Clause OR Apache-2.0 WITH 389-exception)"
    ) == [
        "(",
        "DocumentRef-spdx-tool-1.2:LicenseRef-MIT-Style-2",
        "OR",
        "(",
        "Apache-2.0",
        "AND",
        "PostgreSQL",
        "OR",
        "OpenSSL",
        ")",
        ")",
        "AND",
        "(",
        "BSD-3-Clause",
        "OR",
        "Apache-2.0 WITH 389-exception",
        ")",
    ]


def license_str_to_html(license_str: str) -> str:
    """return the license_str with links to the license"""

    def make_link(license_str: str) -> str:
        return f'<a href="#{sha1(license_str.encode(), usedforsecurity=False).hexdigest()}">{license_str}</a>'

    ret_str = ""
    for token in tokenize(license_str):
        if token in ("(", ")"):
            ret_str += token
        elif token in ("AND", "OR"):
            ret_str += " " + token + " "
        else:
            ret_str += make_link(token)
    return ret_str


def test_license_str_to_html() -> None:
    assert (
        license_str_to_html("MIT AND BSD-3-Clause AND Zlib")
        == '<a href="#89690ac571dcf4c9c40c842efed3f11171d07b29">MIT</a> AND <a href="#d6f9c69f2854ede6f6c6c74c61a8e511654060d0">BSD-3-Clause</a> AND <a href="#11bb391f0b17e28b6022b1e54849a09b53bb2edb">Zlib</a>'
    )
    assert (
        license_str_to_html("BSD-3-Clause")
        == '<a href="#d6f9c69f2854ede6f6c6c74c61a8e511654060d0">BSD-3-Clause</a>'
    )


class MyDocTemplate(SimpleDocTemplate):  # type: ignore[misc]
    """Custom DocTemplate configured for handling of table of contents"""

    def __init__(self, filename, **kw) -> None:
        self.allowSplitting = 0
        SimpleDocTemplate.__init__(self, filename, **kw)
        template = PageTemplate("normal", [Frame(2.5 * cm, 2.5 * cm, 15 * cm, 25 * cm, id="F1")])
        self.addPageTemplates(template)

    def afterFlowable(self, flowable):
        # Registers TOC entries
        if flowable.__class__.__name__ == "Paragraph":
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == "Heading1":
                level = 0
            elif style == "Heading2":
                level = 1
            else:
                return

            E = [level, text, self.page]
            # If we have a bookmark name append that to our notify data
            bn = getattr(flowable, "_bookmarkName", None)
            if bn is not None:
                E.append(bn)
            self.notify("TOCEntry", tuple(E))


def heading(text: str, link: str, sty: PS) -> Paragraph:
    """make a heading"""
    # Create bookmarkname
    bn = sha1(link.encode("utf-8"), usedforsecurity=False).hexdigest()
    # Modify paragraph text to include an anchor point with name bn
    h = Paragraph(f'{text}<a name="{bn}"/>', sty)
    # Store the bookmark name on the flowable so afterFlowable can see this
    h._bookmarkName = bn  # pylint: disable=protected-access  # noqa: SLF001
    return h


def add_page_number(canvas, _doc) -> None:
    page_num = canvas.getPageNumber()
    if page_num < 1:
        return
    text = "%s" % page_num
    canvas.setFont("Calibri", 12)
    canvas.drawRightString(20 * cm, 1 * cm, text)


@dataclass(frozen=True)
class Dependency:
    name: str
    version: str
    license_str: str


def read_license_csv(path_licenses_csv: Path) -> list[Dependency]:
    with path_licenses_csv.open() as csv_file:
        reader = csv.DictReader(csv_file)
        return [
            Dependency(name=row["Name"], version=row["Version"], license_str=row["License"])
            for row in reader
            if row["Version"] or row["License"]
        ]


def setup_document(path_pdf: Path, path_logo: Path) -> tuple[MyDocTemplate, list]:
    doc = MyDocTemplate(
        str(path_pdf),
        pagesize=letter,
        bottomMargin=0.4 * inch,
        topMargin=0.6 * inch,
        rightMargin=0.8 * inch,
        leftMargin=0.8 * inch,
    )
    toc = TableOfContents()
    toc.levelStyles = [
        PS(
            fontName="Calibri",
            fontSize=14,
            name="TOCHeading1",
            leftIndent=20,
            firstLineIndent=-20,
            spaceBefore=5,
            leading=16,
        ),
        PS(fontSize=12, name="TOCHeading2", leftIndent=40, firstLineIndent=-20, leading=12),
    ]
    cover = PS(name="Cover", fontSize=16, leading=22, alignment=1)
    title = PS(name="Title", fontSize=24, leading=16)
    spacer = Spacer(width=0, height=2 * cm)

    drawing = svg2rlg(str(path_logo))
    sx = sy = 2
    drawing.width, drawing.height = drawing.minWidth() * sx, drawing.height * sy
    drawing.scale(sx, sy)
    cover_logo = Image(drawing)
    cover_logo.hAllign = "CENTER"
    cover_text = "Open Source licenses included in:<br /><br />\n\
            Checkmk Enterprise Edition<br />\n\
            Checkmk Managed Services Edition"

    story = []
    story.append(Spacer(width=0, height=6 * cm))
    story.append(cover_logo)
    story.append(Spacer(width=0, height=1 * cm))
    story.append(Paragraph(cover_text, cover))
    story.append(PageBreak())
    story.append(Paragraph("<b>Content</b>", title))
    story.append(spacer)
    story.append(toc)

    return doc, story


def used_licenses(dependencies: list[Dependency]) -> list[str]:
    return sorted(
        {
            token
            for d in dependencies
            for token in tokenize(d.license_str)
            if token not in ("(", ")", "AND", "OR")
        }
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, required=True)
    return parser.parse_args()


def main():
    args = _parse_args()

    path_omd = Path(__file__).resolve().parent.parent
    path_license_texts = path_omd / "license_sources/license_texts/"
    path_pdf = args.pdf
    path_logo = path_omd / "license_sources/checkmk_logo.svg"
    path_licenses_csv = args.csv

    dependencies = read_license_csv(path_licenses_csv)

    registerFont(TTFont("Calibri", path_omd / "license_sources" / "Calibri.ttf"))

    doc, story = setup_document(path_pdf, path_logo)

    h1 = PS(name="Heading1", fontSize=16, leading=16, spaceAfter=1 * cm)
    h2 = PS(name="Heading2", fontSize=14, leading=16)
    normal = PS(name="Normal", fontSize=8)

    story.append(PageBreak())
    story.append(heading("Used libraries", "used_libraries", h1))
    for dependency in dependencies:
        story.append(
            Paragraph(
                f"{dependency.name}, {dependency.version}: {license_str_to_html(dependency.license_str)}",
                normal,
                bulletText="-",
            )
        )

    story.append(PageBreak())
    story.append(heading("Licenses", "libraries", h1))

    for used_license in used_licenses(dependencies):
        file_path = path_license_texts / ("%s.txt" % used_license.lower().replace(" ", "_"))
        if file_path.is_file():
            with file_path.open(encoding="utf-8") as txt_file:
                headline = f"<b>{txt_file.readline().strip()} ({used_license})</b>"
                text_content = html.escape(txt_file.read()).replace("\n", "<br />\n")
            story.append(PageBreak())
            story.append(heading(headline, used_license, h2))
            story.append(Paragraph(text_content, normal))
        else:
            raise RuntimeError(
                f'No license text file found for ID "{used_license}" and path {file_path}'
            )

    doc.multiBuild(story, onLaterPages=add_page_number)


if __name__ == "__main__":
    main()
