#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.i18n import _l
from cmk.gui.log import logger
from cmk.gui.type_defs import Row
from cmk.gui.views.sorter import Sorter

from .base import Perfometer


def sort_perfometer(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, object] | None,
    config: Config,
    request: Request,
) -> int:
    try:
        v1 = tuple(-float("inf") if s is None else s for s in Perfometer(r1).sort_value())
        v2 = tuple(-float("inf") if s is None else s for s in Perfometer(r2).sort_value())
        return (v1 > v2) - (v1 < v2)
    except Exception:
        logger.exception("error sorting perfometer values")
        if config.debug:
            raise
        return 0


SorterPerfometer = Sorter(
    ident="perfometer",
    title=_l("Perf-O-Meter"),
    columns=[
        "service_perf_data",
        "service_state",
        "service_check_command",
        "service_pnpgraph_present",
        "service_plugin_output",
    ],
    sort_function=sort_perfometer,
)
