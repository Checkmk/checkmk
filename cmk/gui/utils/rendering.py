#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Iterable,
    Optional,
    Tuple,
)

from cmk.gui.globals import html
from cmk.gui.i18n import _u
from cmk.gui.utils.html import HTML
from cmk.gui.escaping import escape_text


def text_with_links_to_user_translated_html(
    elements: Iterable[Tuple[str, Optional[str]]],
    separator: str = "",
) -> HTML:
    return HTML(separator).join(
        html.render_a(user_translation, href=url) if url else escape_text(user_translation)
        for txt, url in elements
        for user_translation in [_u(txt)]
        if txt)
