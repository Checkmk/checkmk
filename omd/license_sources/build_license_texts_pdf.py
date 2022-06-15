#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Python module for generating a PDF containing all license texts that can be
found under ./license_texts/"""

import sys
import traceback
import argparse
import csv

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle as PS
from reportlab.lib.units import inch, cm
from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, PageBreak
from reportlab.platypus.doctemplate import PageTemplate
from reportlab.platypus.frames import Frame
from reportlab.platypus.tableofcontents import TableOfContents


class MyDocTemplate(SimpleDocTemplate):
    """Custom DocTemplate configured for handling of table of contents"""
    def __init__(self, filename, **kw) -> None:
        self.allowSplitting = 0
        SimpleDocTemplate.__init__(self, filename, **kw)
        template = PageTemplate('normal', [Frame(2.5 * cm, 2.5 * cm, 15 * cm, 25 * cm, id='F1')])
        self.addPageTemplates(template)

    def afterFlowable(self, flowable):
        # Registers TOC entries
        if flowable.__class__.__name__ == 'Paragraph':
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == 'Heading1':
                level = 0
            elif style == 'Heading2':
                level = 1
            else:
                return

            E = [level, text, self.page]
            # If we have a bookmark name append that to our notify data
            bn = getattr(flowable, '_bookmarkName', None)
            if bn is not None:
                E.append(bn)
            self.notify('TOCEntry', tuple(E))


# This function makes our headings
def heading(text, sty):
    from hashlib import sha1
    # Create bookmarkname
    bn = sha1((text + sty.name).encode("utf-8")).hexdigest()
    # Modify paragraph text to include an anchor point with name bn
    h = Paragraph(text + '<a name="%s"/>' % bn, sty)
    # Store the bookmark name on the flowable so afterFlowable can see this
    h._bookmarkName = bn
    return h


def add_page_number(canvas, doc):
    page_num = canvas.getPageNumber()
    if page_num < 4:
        return
    text = "%s" % page_num
    canvas.setFont("Calibri", 12)
    canvas.drawRightString(20 * cm, 1 * cm, text)


def used_licenses_from_csv(path_licenses_csv):
    used_licenses = []
    with open(path_licenses_csv, "r") as csv_file:
        csv_file.readline()  # Drop line of headers
        rows = list(csv.reader(csv_file))
        used_licenses = {row[2] for row in rows if row[2]}
    return sorted(used_licenses)


def main():
    try:
        path_omd = Path(__file__).resolve().parent.parent
    except:
        raise OSError

    path_license_texts = path_omd / "license_sources/license_texts/"
    path_pdf = path_omd / "License_texts.pdf"
    path_logo = path_omd / "license_sources/check_mk_logo_large1.png"
    path_licenses_csv = path_omd / "Licenses.csv"

    used_licenses = used_licenses_from_csv(path_licenses_csv)

    registerFont(TTFont('Calibri', 'Calibri.ttf'))
    doc = SimpleDocTemplate(str(path_pdf),
                            pagesize=letter,
                            bottomMargin=.4 * inch,
                            topMargin=.6 * inch,
                            rightMargin=.8 * inch,
                            leftMargin=.8 * inch)
    toc = TableOfContents()
    toc.levelStyles = [
        PS(fontName='Calibri',
           fontSize=14,
           name='TOCHeading1',
           leftIndent=20,
           firstLineIndent=-20,
           spaceBefore=5,
           leading=16),
        PS(fontSize=12, name='TOCHeading2', leftIndent=40, firstLineIndent=-20, leading=12),
    ]
    cover = PS(name='Cover', fontSize=16, leading=22, alignment=1)
    title = PS(name='Title', fontSize=24, leading=16)
    h1 = PS(name='Heading1', fontSize=16, leading=16)
    normal = PS(name='Normal', fontSize=8)
    spacer = Spacer(width=0, height=2 * cm)

    cover_logo = Image(str(path_logo), width=3.5 * inch, height=1 * inch)
    cover_text = "Open Source licenses included in:<br /><br />\n\
            Checkmk Enterprise Edition<br />\n\
            Checkmk Managed Services Edition"

    story = []
    story.append(Spacer(width=0, height=6 * cm))
    story.append(cover_logo)
    story.append(Spacer(width=0, height=1 * cm))
    story.append(Paragraph(cover_text, cover))
    story.append(PageBreak())
    story.append(Paragraph('<b>Content</b>', title))
    story.append(spacer)
    story.append(toc)

    for used_license in used_licenses:
        if used_license == "Public-Domain":
            continue

        file_path = path_license_texts / ("%s.txt" % used_license.lower())
        if file_path.is_file():
            with file_path.open(encoding="utf-8") as txt_file:
                headline = "<b>%s</b>" % txt_file.readline().replace("\n", "<br /><br />\n")
                text_content = txt_file.read().replace("\n", "<br />\n")
            story.append(PageBreak())
            story.append(heading(headline, h1))
            story.append(Paragraph(text_content, normal))
        else:
            print("No license text file found for ID \"%s\" and path %s" %
                  (used_license, file_path))

    doc = MyDocTemplate(str(path_pdf))
    doc.multiBuild(story, onLaterPages=add_page_number)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception:
        sys.stderr.write(traceback.format_exc())
        sys.exit(1)
