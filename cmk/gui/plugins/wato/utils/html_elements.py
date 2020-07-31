#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.globals import html
from cmk.gui.breadcrumb import Breadcrumb
# TODO: Change all call sites to directly import from cmk.gui.page_menu
from cmk.gui.page_menu import search_form  # noqa: F401 # pylint: disable=unused-import

# TODO: Refactor to context handler or similar?
_html_head_open = False


# Show confirmation dialog, send HTML-header if dialog is shown.
def wato_confirm(html_title, message):
    if not html.request.has_var("_do_confirm") and not html.request.has_var("_do_actions"):
        # TODO: get the breadcrumb from all call sites
        wato_html_head(html_title, Breadcrumb())
    return html.confirm(message)


def initialize_wato_html_head():
    global _html_head_open
    _html_head_open = False


# TODO: Check all call sites and clean up args/kwargs
def wato_html_head(title: str, breadcrumb: Breadcrumb, *args, **kwargs) -> None:
    global _html_head_open

    if _html_head_open:
        return

    _html_head_open = True
    html.header(title, breadcrumb, *args, **kwargs)
    html.open_div(class_="wato")


def wato_html_footer(show_footer: bool = True, show_body_end: bool = True) -> None:
    if not _html_head_open:
        return

    html.close_div()
    html.footer(show_footer, show_body_end)
