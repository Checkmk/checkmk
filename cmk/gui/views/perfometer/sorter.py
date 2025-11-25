#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.graphing.v1 import perfometers as perfometers_api
from cmk.gui.config import Config
from cmk.gui.graphing import (
    metrics_from_api,
    perfometers_from_api,
    RegisteredMetric,
)
from cmk.gui.http import Request
from cmk.gui.i18n import _l
from cmk.gui.log import logger
from cmk.gui.type_defs import Row
from cmk.gui.views.sorter import Sorter

from .base import Perfometer


def _sort_perfometer(
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_perfometers: Mapping[
        str,
        perfometers_api.Perfometer | perfometers_api.Bidirectional | perfometers_api.Stacked,
    ],
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, object] | None,
    config: Config,
    request: Request,
) -> int:
    try:
        v1 = tuple(
            -float("inf") if s is None else s
            for s in Perfometer(r1, registered_metrics, registered_perfometers).sort_value()
        )
        v2 = tuple(
            -float("inf") if s is None else s
            for s in Perfometer(r2, registered_metrics, registered_perfometers).sort_value()
        )
        return (v1 > v2) - (v1 < v2)
    except Exception:
        logger.exception("error sorting perfometer values")
        if config.debug:
            raise
        return 0


class _SorterPerfometer(Sorter):
    def __init__(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        registered_perfometers: Mapping[
            str,
            perfometers_api.Perfometer | perfometers_api.Bidirectional | perfometers_api.Stacked,
        ],
    ) -> None:
        super().__init__(
            "perfometer",
            _l("Perf-O-Meter"),
            [
                "service_perf_data",
                "service_state",
                "service_check_command",
                "service_pnpgraph_present",
                "service_plugin_output",
            ],
            lambda *args, **kwargs: _sort_perfometer(
                registered_metrics, registered_perfometers, *args, **kwargs
            ),
        )


SorterPerfometer = _SorterPerfometer(metrics_from_api, perfometers_from_api)
