#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Optional, Tuple

from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _u
from cmk.gui.utils.escaping import escape_to_html_permissive
from cmk.gui.utils.html import HTML


def text_with_links_to_user_translated_html(
    elements: Iterable[Tuple[str, Optional[str]]],
    separator: str = "",
) -> HTML:
    return HTML(separator).join(
        HTMLWriter.render_a(user_translation, href=url, title=user_translation)
        if url
        else escape_to_html_permissive(user_translation, escape_links=False)
        for txt, url in elements
        for user_translation in [_u(txt)]
        if txt
    )
