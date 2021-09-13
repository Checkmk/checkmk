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
from typing import Optional, Union

from cmk.gui.globals import html
from cmk.gui.type_defs import CSSSpec
from cmk.gui.utils.html import HTML


@dataclass
class PageState:
    text: Union[str, HTML]
    icon_name: Optional[str] = None
    css_classes: CSSSpec = None
    url: Optional[str] = None
    tooltip_text: str = ""


class PageStateRenderer:
    def show(self, page_state: PageState) -> None:
        html.open_div(class_=self._get_css_classes(page_state), title=page_state.tooltip_text)
        if page_state.url:
            html.open_a(page_state.url)
            self._show_content(page_state)
            html.close_a()
        else:
            self._show_content(page_state)
        html.close_div()

    def _show_content(self, page_state: PageState) -> None:
        html.div(page_state.text, class_="text_container")
        if page_state.icon_name:
            html.div(
                html.render_icon(page_state.icon_name, id_="page_state_icon"),
                class_="icon_container",
            )

    def _get_css_classes(self, page_state: PageState) -> CSSSpec:
        classes = ["page_state"]
        if isinstance(page_state.css_classes, list):
            classes.extend(c for c in page_state.css_classes if c is not None)
        elif page_state.css_classes is not None:
            classes.append(page_state.css_classes)
        return classes
