#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence

from cmk.ccc.plugin_registry import Registry

from cmk.gui.type_defs import Rows
from cmk.gui.view import View
from cmk.gui.visuals.filter import Filter


def post_process_rows(
    view: View,
    all_active_filters: Sequence[Filter],
    rows: Rows,
) -> None:
    """Extend the rows fetched from livestatus with additional information

    For example:
        - Add HW/SW Inventory data when needed
        - Add SLA data when needed (Enterprise editions only)
    """
    if not rows:
        return

    for func in row_post_processor_registry.values():
        func(view, all_active_filters, rows)


RowPostProcessor = Callable[[View, Sequence[Filter], Rows], None]


class RowPostProcessorRegistry(Registry[RowPostProcessor]):
    def plugin_name(self, instance: RowPostProcessor) -> str:
        return f"{instance.__module__}.{instance.__name__}"


row_post_processor_registry = RowPostProcessorRegistry()
