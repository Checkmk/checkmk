#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Optional

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _


def validate_regex(value: str, varname: Optional[str]) -> None:
    try:
        re.compile(value)
    except re.error:
        raise MKUserError(
            varname,
            _(
                "Your search statement is not valid. You need to provide a regular "
                "expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> "
                "if you like to search for a single backslash."
            ),
        )

    # livestatus uses re2 and re can not validate posix pattern, so we have to
    # check for lookaheads here
    lookahead_pattern = r"\((\?!|\?=|\?<)"

    if re.search(lookahead_pattern, value):
        raise MKUserError(
            varname, _("Your search statement is not valid. You can not use a lookahead here.")
        )
