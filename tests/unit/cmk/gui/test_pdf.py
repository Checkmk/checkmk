#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import io
from pathlib import Path

from pypdf import PdfReader

from cmk.gui.pdf import Document
from cmk.gui.type_defs import SizePT

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="
)


def _render_icon_table(icon_path: Path) -> PdfReader:
    doc = Document(
        font_family="Helvetica",
        font_size=SizePT(10.0),
        lineheight=1.2,
        pagesize=(210.0, 297.0),
        margins=(20.0, 20.0, 20.0, 20.0),
    )
    doc.add_table(
        header_texts=["Icon"],
        raw_rows=[[([], ("icon", str(icon_path)))]],
        font_size=SizePT(10.0),
        show_headings=True,
        padding=(1.0, 1.0),
        spacing=(0.0, 0.0),
        hrules=False,
        vrules=False,
        rule_width=0.1,
        row_shading={
            "enabled": False,
            "odd": (1.0, 1.0, 1.0),
            "even": (1.0, 1.0, 1.0),
            "heading": (1.0, 1.0, 1.0),
        },
    )
    pdf_source = doc.end(do_send=False)
    assert pdf_source is not None
    return PdfReader(io.BytesIO(pdf_source))


def test_svg_icon_without_png_is_left_out(tmp_path: Path) -> None:
    svg_path = tmp_path / "icon_agents.svg"
    svg_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')

    reader = _render_icon_table(svg_path)

    assert not reader.pages[0].images


def test_svg_icon_is_drawn_from_its_png(tmp_path: Path) -> None:
    svg_path = tmp_path / "icon_downtime.svg"
    svg_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    (tmp_path / "icon_downtime.png").write_bytes(_ONE_PIXEL_PNG)

    reader = _render_icon_table(svg_path)

    assert len(reader.pages[0].images) == 1
