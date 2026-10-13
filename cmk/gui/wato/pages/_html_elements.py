#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import g
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.logged_in import user
from cmk.gui.page_menu import PageMenu


@contextmanager
def wato_html_page(*, show_body_end: bool) -> Iterator[None]:
    """Scope of a Setup page

    The head is opened by the first call of wato_html_head() within this scope. This may already
    happen during the action of a mode, e.g. to show a confirmation. When the page is complete, the
    elements opened by the head are closed. When the page processing ends with an exception, the
    exception handler is responsible for the response."""
    # Request local, because a page is processed by one request
    g.wato_html_head_open = False
    yield
    if g.wato_html_head_open:
        html.close_div()
        html.footer(show_body_end)


def wato_html_head(
    *,
    title: str,
    breadcrumb: Breadcrumb,
    page_menu: PageMenu | None = None,
    show_body_start: bool = True,
    show_top_heading: bool = True,
) -> None:
    if g.wato_html_head_open:
        return

    g.wato_html_head_open = True
    make_header(
        html,
        title=title,
        breadcrumb=breadcrumb,
        page_menu=page_menu,
        show_body_start=show_body_start,
        show_top_heading=show_top_heading,
        debug=active_config.debug,
        lang=user.language,
        inject_js_profiling_code=active_config.inject_js_profiling_code,
        load_frontend_vue=active_config.load_frontend_vue,
        custom_style_sheet=active_config.custom_style_sheet,
        screenshotmode=active_config.screenshotmode,
        inline_help_as_text=user.inline_help_as_text,
        hide_suggestions=not user.get_tree_state("suggestions", "all", True),
        user_role_ids=user.role_ids,
    )
    html.open_div(class_="wato")
