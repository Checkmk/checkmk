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
from cmk.gui.type_defs import CSSSpec


@dataclass
class PageState:
    top_line: Union[str, HTML]
    bottom_line: Union[str, HTML]
    icon_name: str
    css_classes: CSSSpec = None


class PageStateRenderer:
    def show(self, page_state: PageState) -> None:
        html.open_div(class_=self._get_css_classes(page_state))

        html.open_div(class_="text")

        html.open_span()
        html.span(page_state.top_line, id_="page_state_top_line")
        html.span("", id_="headinfo")
        html.close_span()

        html.span(page_state.bottom_line)
        html.close_div()

        html.open_div(class_="icon_container")
        html.icon(page_state.icon_name, id_="page_state_icon")
        html.close_div()

        html.close_div()

    def _get_css_classes(self, page_state: PageState) -> CSSSpec:
        classes = ["page_state"]
        if isinstance(page_state.css_classes, list):
            classes.extend(c for c in page_state.css_classes if c is not None)
        elif page_state.css_classes is not None:
            classes.append(page_state.css_classes)
        return classes
