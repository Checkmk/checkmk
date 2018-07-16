#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _
from cmk.gui.globals import html

wato_styles = [ "pages", "wato", "status" ]

# TODO: Refactor to context handler or similar?
_html_head_open = False

# Show confirmation dialog, send HTML-header if dialog is shown.
def wato_confirm(html_title, message):
    if not html.has_var("_do_confirm") and not html.has_var("_do_actions"):
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
    html.header(title, *args, javascripts=["wato"], stylesheets=wato_styles, **kwargs)
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
        html.write_text(title+' ')
    html.text_input("search", size=32, default_value=default_value)
    html.hidden_fields()
    if mode:
        html.hidden_field("mode", mode, add_var=True)
    html.set_focus("search")
    html.write_text(" ")
    html.button("_do_seach", _("Search"))
    html.end_form()
