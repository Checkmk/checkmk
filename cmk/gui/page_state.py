#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Rendering the page state (top right of the page header)

Cares about the page state rendering. Each page can produce a page state that is displayed on the
top right of the page.
"""

from dataclasses import dataclass
from typing import Union

from cmk.gui.globals import html
from cmk.gui.utils.html import HTML


@dataclass
class PageState:
    top_line: Union[str, HTML]
    bottom_line: Union[str, HTML]
    icon_name: str


class PageStateRenderer:
    def show(self, page_state: PageState) -> None:
        html.open_div(class_="page_state")

        html.open_div(class_="text")
        html.span(page_state.top_line)
        html.span(page_state.bottom_line)
        html.close_div()

        html.icon(None, page_state.icon_name)

        html.close_div()
