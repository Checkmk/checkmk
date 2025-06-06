#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.page_menu import PageMenu

# TODO: Refactor to context handler or similar?
_html_head_open = False


def initialize_wato_html_head() -> None:
    global _html_head_open
    _html_head_open = False


def wato_html_head(
    *,
    title: str,
    breadcrumb: Breadcrumb,
    page_menu: PageMenu | None = None,
    show_body_start: bool = True,
    show_top_heading: bool = True,
) -> None:
    global _html_head_open

    if _html_head_open:
        return

    _html_head_open = True
    make_header(
        html,
        title=title,
        breadcrumb=breadcrumb,
        page_menu=page_menu,
        show_body_start=show_body_start,
        show_top_heading=show_top_heading,
    )
    html.open_div(class_="wato")


def wato_html_footer(show_body_end: bool = True) -> None:
    if not _html_head_open:
        return

    html.close_div()
    html.footer(show_body_end)
