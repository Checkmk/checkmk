#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.globals import html

# TODO: Refactor to context handler or similar?
_html_head_open = False


# Show confirmation dialog, send HTML-header if dialog is shown.
def wato_confirm(html_title, message):
    if not html.request.has_var("_do_confirm") and not html.request.has_var("_do_actions"):
        wato_html_head(html_title)
    return html.confirm(message)


def initialize_wato_html_head():
    global _html_head_open
    _html_head_open = False


def wato_html_head(title, *args, **kwargs):
    global _html_head_open

    if _html_head_open:
        return

    _html_head_open = True
    html.header(title, *args, **kwargs)
    html.open_div(class_="wato")


def wato_html_footer(*args, **kwargs):
    if not _html_head_open:
        return

    html.close_div()
    html.footer(*args, **kwargs)


# TODO: Cleanup all calls using title and remove the argument
def search_form(title=None, mode=None, default_value=""):
    html.begin_form("search", add_transid=False)
    if title:
        html.write_text(title + ' ')
    html.text_input("search", size=32, default_value=default_value)
    html.hidden_fields()
    if mode:
        html.hidden_field("mode", mode, add_var=True)
    html.set_focus("search")
    html.write_text(" ")
    html.button("_do_seach", _("Search"))
    html.end_form()
