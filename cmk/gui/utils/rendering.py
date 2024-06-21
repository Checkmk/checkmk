#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable

from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _u
from cmk.gui.utils.escaping import escape_to_html_permissive
from cmk.gui.utils.html import HTML


def text_with_links_to_user_translated_html(
    elements: Iterable[tuple[str, str | None]],
    separator: HTML | None = None,
) -> HTML:
    if separator is None:
        separator = HTML.empty()

    return separator.join(
        (
            HTMLWriter.render_a(user_translation, href=url, title=user_translation)
            if url
            else escape_to_html_permissive(user_translation, escape_links=False)
        )
        for txt, url in elements
        for user_translation in [_u(txt)]
        if txt
    )


def set_inpage_search_result_info(search_results: int) -> None:
    html.javascript(
        "cmk.utils.set_inpage_search_result_info(%s);"
        % json.dumps(_("Results: %d") % search_results if search_results else _("No results"))
    )
