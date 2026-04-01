#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.html import HTMLGenerator
from cmk.gui.page_menu import PageMenu
from cmk.gui.top_heading import top_heading


def make_header(
    writer: HTMLGenerator,
    title: str,
    breadcrumb: Breadcrumb,
    page_menu: PageMenu | None = None,
    force: bool = False,
    show_body_start: bool = True,
    show_top_heading: bool = True,
    enable_main_page_scrollbar: bool = True,
    *,
    debug: bool,
    lang: str,
    inject_js_profiling_code: bool,
    load_frontend_vue: str,
    custom_style_sheet: str | None,
    screenshotmode: bool,
    inline_help_as_text: bool,
    hide_suggestions: bool,
    user_role_ids: Sequence[str],
) -> None:
    if writer.output_format != "html":
        return

    if not writer._header_sent:
        if show_body_start:
            writer.body_start(
                title,
                force=force,
                lang=lang,
                inject_js_profiling_code=inject_js_profiling_code,
                load_frontend_vue=load_frontend_vue,
                custom_style_sheet=custom_style_sheet,
                screenshotmode=screenshotmode,
                inline_help_as_text=inline_help_as_text,
            )

        writer._header_sent = True

        breadcrumb = breadcrumb or Breadcrumb()

        if writer.render_headfoot and show_top_heading:
            top_heading(
                writer,
                writer.request,
                title,
                breadcrumb=breadcrumb,
                page_menu=page_menu or PageMenu(breadcrumb=breadcrumb),
                browser_reload=writer.browser_reload,
                debug=debug,
                hide_suggestions=hide_suggestions,
                user_role_ids=user_role_ids,
            )

    writer.begin_page_content(enable_scrollbar=enable_main_page_scrollbar)
