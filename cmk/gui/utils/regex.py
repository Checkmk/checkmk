#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.utils.urls import doc_reference_url, DocReference


def validate_regex(value: str, varname: str | None) -> None:
    try:
        re.compile(value)
    except re.error:
        raise MKUserError(
            varname,
            _(
                "Your search statement is not valid. You need to provide a %s (regex). For example "
                "you need to use <tt>\\\\</tt> instead of <tt>\\</tt> if you like to search for a "
                "single backslash."
            )
            % html.render_a(
                "regular expression",
                href=doc_reference_url(DocReference.REGEXES),
                target="_blank",
            ),
        )

    # livestatus uses re2 and re can not validate posix pattern, so we have to
    # check for lookaheads here
    lookahead_pattern = r"\((\?!|\?=|\?<)"

    if re.search(lookahead_pattern, value):
        raise MKUserError(
            varname, _("Your search statement is not valid. You can not use a lookahead here.")
        )
