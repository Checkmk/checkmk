#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import assert_never, Final

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    evaluate_perfometer,
    EvaluatedBidirectional,
    EvaluatedPerfometer,
    EvaluatedPerfometerLayout,
    EvaluatedStacked,
    HostName,
    parse_performance_data,
    PerfometerIndex,
    Service,
    ServiceName,
    translate_performance_data,
    Unit,
)
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.log import logger
from cmk.gui.utils.temperature_unit import TemperatureUnit

from ._user_specific_unit import user_specific_unit


def _render_value(value: float, unit: Unit, temperature_unit: TemperatureUnit) -> str:
    specific = user_specific_unit(unit, temperature_unit)
    return specific.formatter.render(specific.conversion(value))


def _bar_label(bar: EvaluatedPerfometer, temperature_unit: TemperatureUnit) -> str:
    return _render_value(
        sum(segment.value for segment in bar.segments),
        bar.segments[0].attributes.unit,
        temperature_unit,
    )


def perfometer_label(
    perfometer: EvaluatedPerfometerLayout, temperature_unit: TemperatureUnit
) -> str:
    match perfometer:
        case EvaluatedPerfometer():
            return _bar_label(perfometer, temperature_unit)
        case EvaluatedBidirectional():
            bars = (perfometer.left, perfometer.right)
        case EvaluatedStacked():
            bars = (perfometer.upper, perfometer.lower)
        case _:
            assert_never(perfometer)
    return " / ".join(label for bar in bars if (label := _bar_label(bar, temperature_unit)))


_SUPERSEDED_TO_SUPERSEDER: Final[Mapping[str, str]] = {
    "backup_size": "backup_age",
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
    registered_perfometers: PerfometerIndex,
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    debug: bool,
) -> EvaluatedPerfometerLayout | None:
    if not (perf_data_string := perf_data_string.strip()):
        return None
    raw = parse_performance_data(perf_data_string, check_command, debug=debug, logger=logger)
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
