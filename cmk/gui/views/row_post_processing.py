#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence

from cmk.gui.plugins.visuals.utils import Filter
from cmk.gui.type_defs import Rows
from cmk.gui.view import View

_ROW_POST_PROCESSORS: list[Callable[[View, Sequence[Filter], Rows], None]] = []


def post_process_rows(
    view: View,
    all_active_filters: Sequence[Filter],
    rows: Rows,
) -> None:
    """Extend the rows fetched from livestatus with additional information

    For example:
        - Add HW/SW inventory data when needed
        - Add SLA data when needed (Enterprise editions only)
    """
    if not rows:
        return

    for func in _ROW_POST_PROCESSORS:
        func(view, all_active_filters, rows)


def register_row_post_processor(func: Callable[[View, Sequence[Filter], Rows], None]) -> None:
    _ROW_POST_PROCESSORS.append(func)
