#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.breadcrumb import make_simple_page_breadcrumb
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.pages import Page, PageRegistry, PageResult


class GuiTimingsPage(Page):
    def _title(self) -> str:
        return "GUI timings"

    def page(self) -> PageResult:
        breadcrumb = make_simple_page_breadcrumb(mega_menu_registry["help"], _("Info"))
        make_header(
            html,
            self._title(),
            breadcrumb=breadcrumb,
        )

        html.open_div(id_="info_title")
        html.h1("Client side GUI timings")
        html.close_div()

        html.div(None, id_="info_underline")

        html.call_ts_function(
            container="div",
            function_name="render_stats_table",
            arguments=None,
        )

        html.final_javascript_code()
        html.close_body()
        return None


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page("gui_timings")(GuiTimingsPage)
