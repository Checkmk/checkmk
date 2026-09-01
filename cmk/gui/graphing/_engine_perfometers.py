#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Final

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    evaluate_perfometer,
    EvaluatedPerfometerLayout,
    HostName,
    Service,
    ServiceName,
)
from cmk.gui.i18n import translate_to_current_language

from ._engine_perfdata import parse_performance_data
from ._engine_translations import translate_performance_data
from ._from_api import PerfometerFromAPI

_SUPERSEDED_TO_SUPERSEDER: Final[Mapping[str, str]] = {
    "mem_used_perc": "mem_used_percent",
    "mem_used_with_dynamic_range": "mem_used_percent",
    "mem_used": "mem_used_percent",
}


def evaluated_perfometer(
    perf_data_string: str,
    check_command: str,
    *,
    host_name: str,
    service_name: str,
    registered_perfometers: Mapping[str, PerfometerFromAPI],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    debug: bool,
) -> EvaluatedPerfometerLayout | None:
    if not (perf_data_string := perf_data_string.strip()):
        return None
    raw = parse_performance_data(perf_data_string, check_command, debug=debug)
    if not raw.values:
        return None
    return evaluate_perfometer(
        localizer=translate_to_current_language,
        service=Service(host_name=HostName(host_name), service_name=ServiceName(service_name)),
        performance_data=translate_performance_data(
            raw.check_command, raw.values, registered_translations
        ),
        registered_perfometers=registered_perfometers,
        registered_metrics=registered_metrics,
        superseders=_SUPERSEDED_TO_SUPERSEDER,
    )
