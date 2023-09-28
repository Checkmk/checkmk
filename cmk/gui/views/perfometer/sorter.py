#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.type_defs import ColumnName, Row
from cmk.gui.views.sorter import Sorter

from .base import Perfometer


class SorterPerfometer(Sorter):
    @property
    def ident(self) -> str:
        return "perfometer"

    @property
    def title(self) -> str:
        return _("Perf-O-Meter")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return [
            "service_perf_data",
            "service_state",
            "service_check_command",
            "service_pnpgraph_present",
            "service_plugin_output",
        ]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, object] | None) -> int:
        try:
            v1 = tuple(-float("inf") if s is None else s for s in Perfometer(r1).sort_value())
            v2 = tuple(-float("inf") if s is None else s for s in Perfometer(r2).sort_value())
            return (v1 > v2) - (v1 < v2)
        except Exception:
            logger.exception("error sorting perfometer values")
            if active_config.debug:
                raise
            return 0
