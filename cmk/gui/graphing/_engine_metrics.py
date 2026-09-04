#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    metric_display_attributes,
    MetricName,
    PerformanceData,
)
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.unit_formatter import NotationFormatter
from cmk.gui.utils.temperate_unit import TemperatureUnit

from ._engine_perfdata import parse_performance_data
from ._engine_translations import translate_performance_data
from ._engine_unit_format import unit_to_unit_format
from ._unit import user_specific_unit_from_unit_format


@dataclass(frozen=True, kw_only=True)
class EvaluatedMetric:
    name: MetricName
    title: str
    color: str
    formatter: NotationFormatter
    performance_data: PerformanceData


def _in_user_unit(
    performance_data: PerformanceData, conversion: Callable[[float], float]
) -> PerformanceData:
    def _converted(value: float | None) -> float | None:
        return None if value is None else conversion(value)

    return PerformanceData(
        value=_converted(performance_data.value),
        lower_warning=_converted(performance_data.lower_warning),
        lower_critical=_converted(performance_data.lower_critical),
        warning=_converted(performance_data.warning),
        critical=_converted(performance_data.critical),
        minimum=_converted(performance_data.minimum),
        maximum=_converted(performance_data.maximum),
    )


def evaluated_metrics(
    perf_data_string: str,
    check_command: str,
    rrd_metrics: Sequence[MetricName] = (),
    *,
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    temperature_unit: TemperatureUnit,
    debug: bool,
) -> Mapping[MetricName, EvaluatedMetric]:
    raw = parse_performance_data(perf_data_string, check_command, rrd_metrics, debug=debug)
    evaluated = {}
    for name, performance_data in translate_performance_data(
        raw.check_command, raw.values, registered_translations
    ).items():
        attributes = metric_display_attributes(
            name, translate_to_current_language, registered_metrics
        )
        unit = user_specific_unit_from_unit_format(
            unit_to_unit_format(attributes.unit), temperature_unit
        )
        evaluated[name] = EvaluatedMetric(
            name=name,
            title=attributes.title,
            color=attributes.color,
            formatter=unit.formatter,
            performance_data=_in_user_unit(performance_data, unit.conversion),
        )
    return evaluated
