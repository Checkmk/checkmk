#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.context import html
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.i18n import _

# TODO: Change all call sites to directly import from cmk.gui.page_menu
from cmk.gui.page_menu import PageMenu, search_form  # noqa: F401 # pylint: disable=unused-import
from cmk.gui.page_state import PageState
from cmk.gui.watolib.activate_changes import get_pending_changes_info, get_pending_changes_tooltip

# TODO: Refactor to context handler or similar?
_html_head_open = False


def initialize_wato_html_head():
    global _html_head_open
    _html_head_open = False


def wato_html_head(
    *,
    title: str,
    breadcrumb: Breadcrumb,
    page_menu: Optional[PageMenu] = None,
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
        page_state=_make_wato_page_state(),
        show_body_start=show_body_start,
        show_top_heading=show_top_heading,
    )
    html.open_div(class_="wato")


def wato_html_footer(show_body_end: bool = True) -> None:
    if not _html_head_open:
        return

    html.close_div()
    html.footer(show_body_end)


def _make_wato_page_state() -> PageState:
    changes_info = get_pending_changes_info()
    tooltip = get_pending_changes_tooltip()
    changelog_url = "wato.py?mode=changelog"
    span_id = "changes_info"
    if changes_info:
        changes_number, changes_str = changes_info.split()
        return PageState(
            text=HTMLWriter.render_span(
                HTMLWriter.render_span(changes_number, class_="changes_number")
                + HTMLWriter.render_span(changes_str, class_="changes_str"),
                id_=span_id,
            ),
            icon_name="pending_changes",
            url=changelog_url,
            tooltip_text=tooltip,
            css_classes="pending_changes",
        )
    return PageState(
        text=HTMLWriter.render_span(
            HTMLWriter.render_span("", class_="changes_number")
            + HTMLWriter.render_span(_("No pending changes"), class_="changes_str"),
            id_=span_id,
        ),
        url=changelog_url,
        tooltip_text=tooltip,
        css_classes="no_changes",
    )
