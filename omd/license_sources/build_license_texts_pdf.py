#!/usr/bin/env python
"""Python module for generating a PDF containing all license texts that can be
found under ./license_texts/"""

import sys
import os
import traceback
from pathlib2 import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle as PS
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.platypus.frames import Frame
from reportlab.lib.units import cm
from PyPDF2 import PdfFileMerger, PdfFileReader


class MyDocTemplate(BaseDocTemplate):
    """Custom DocTemplate configured for handling of table of contents"""

    def __init__(self, filename, **kw):
        self.allowSplitting = 0
        apply(BaseDocTemplate.__init__, (self, filename), kw)
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
            if bn is not None: E.append(bn)
            self.notify('TOCEntry', tuple(E))


# This function makes our headings
def heading(text, sty):
    from hashlib import sha1
    # Create bookmarkname
    bn = sha1(text + sty.name).hexdigest()
    # Modify paragraph text to include an anchor point with name bn
    h = Paragraph(text + '<a name="%s"/>' % bn, sty)
    # Store the bookmark name on the flowable so afterFlowable can see this
    h._bookmarkName = bn
    return h


def main():
    try:
        path_omd = Path("%s/git/check_mk/omd/" % Path.home())
        path_license_texts = path_omd / "license_sources/license_texts/"
        path_pdf = path_omd / "License_texts.pdf"
        path_cover = path_omd / "license_sources/licenses_cover.pdf"
    except:
        raise OSError

    registerFont(TTFont('Calibri', 'Calibri.ttf'))
    doc = SimpleDocTemplate(
        str(path_pdf),
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
    title = PS(name='Title', fontSize=24, leading=16)
    h1 = PS(name='Heading1', fontSize=16, leading=16)
    normal = PS(name='Normal', fontSize=8)
    centered = PS(name='centered', fontSize=18, leading=16, alignment=1, spaceAfter=20)
    spacer = Spacer(width=0, height=2 * cm)

    story = []
    story.append(Paragraph('<b>Content</b>', title))
    story.append(spacer)
    story.append(toc)

    for file_path in sorted(path_license_texts.iterdir()):
        with file_path.open(encoding="utf-8") as txt_file:
            headline = "<b>%s</b>" % txt_file.readline().replace("\n", "<br /><br />\n")
            text_content = txt_file.read().replace("\n", "<br />\n")
        story.append(PageBreak())
        story.append(heading(headline, h1))
        story.append(Paragraph(text_content, normal))

    doc = MyDocTemplate(str(path_pdf))
    doc.multiBuild(story)

    pdf_merger = PdfFileMerger()
    pdf_merger.append(PdfFileReader(str(path_cover)))
    pdf_merger.append(PdfFileReader(str(path_pdf)))
    pdf_merger.write(str(path_pdf))


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception:
        sys.stderr.write(traceback.format_exc())
        sys.exit(1)
