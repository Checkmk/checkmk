#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Optional

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.html import HTMLGenerator
from cmk.gui.htmllib.top_heading import top_heading
from cmk.gui.page_menu import PageMenu
from cmk.gui.page_state import PageState


def make_header(
    writer: HTMLGenerator,
    title: str,
    breadcrumb: Breadcrumb,
    page_menu: Optional[PageMenu] = None,
    page_state: Optional[PageState] = None,
    javascripts: Optional[List[str]] = None,
    force: bool = False,
    show_body_start: bool = True,
    show_top_heading: bool = True,
) -> None:
    if writer.output_format != "html":
        return

    if not writer._header_sent:
        if show_body_start:
            writer.body_start(title, javascripts=javascripts, force=force)

        writer._header_sent = True

        breadcrumb = breadcrumb or Breadcrumb()

        if writer.render_headfoot and show_top_heading:
            top_heading(
                writer,
                writer.request,
                title,
                breadcrumb=breadcrumb,
                page_menu=page_menu or PageMenu(breadcrumb=breadcrumb),
                page_state=page_state,
                browser_reload=writer.browser_reload,
            )
    writer.begin_page_content()
