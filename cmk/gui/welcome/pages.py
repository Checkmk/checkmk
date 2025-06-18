#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.pages import Page, PageRegistry


def register(page_registry: PageRegistry) -> None:
    """Register the welcome page."""
    page_registry.register_page("welcome")(WelcomePage)


class WelcomePage(Page):
    @classmethod
    @override
    def ident(cls) -> str:
        return "welcome"

    @override
    def page(self) -> None:
        make_header(html, "Welcome", breadcrumb=Breadcrumb(), show_top_heading=False)
        html.vue_component(component_name="cmk-welcome", data={})
