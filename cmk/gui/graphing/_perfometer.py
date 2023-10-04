#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Any, Literal, NotRequired, TypeAlias, TypedDict

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.metrics import MetricName

from cmk.gui.i18n import _
from cmk.gui.type_defs import TranslatedMetrics

from ._expression import parse_conditional_expression, parse_expression

LegacyPerfometer = tuple[str, Any]


class LinearPerfometerSpec(TypedDict):
    type: Literal["linear"]
    segments: Sequence[str]
    total: int | float | str
    condition: NotRequired[str]
    label: NotRequired[tuple[str, str] | None]  # (expression, unit)
    color: NotRequired[str]


class LogarithmicPerfometerSpec(TypedDict):
    type: Literal["logarithmic"]
    metric: str
    half_value: int | float
    exponent: int | float
    unit: NotRequired[str]


class DualPerfometerSpec(TypedDict):
    type: Literal["dual"]
    perfometers: Sequence[LinearPerfometerSpec | LogarithmicPerfometerSpec]


class StackedPerfometerSpec(TypedDict):
    type: Literal["stacked"]
    perfometers: Sequence[LinearPerfometerSpec | LogarithmicPerfometerSpec | DualPerfometerSpec]


PerfometerSpec: TypeAlias = (
    LinearPerfometerSpec | LogarithmicPerfometerSpec | DualPerfometerSpec | StackedPerfometerSpec
)
perfometer_info: list[LegacyPerfometer | PerfometerSpec] = []


def _get_metric_names(
    perfometer: PerfometerSpec, translated_metrics: TranslatedMetrics
) -> Sequence[MetricName]:
    """Returns all metric names which are used within a perfometer.
    This is used for checking which perfometer can be displayed for a given service later.
    """
    if perfometer["type"] == "linear":
        metric_names = [
            m.name
            for s in perfometer["segments"]
            for m in parse_expression(s, translated_metrics).metrics()
        ]
        if (total := perfometer.get("total")) is not None:
            metric_names += [m.name for m in parse_expression(total, translated_metrics).metrics()]

        if (label := perfometer.get("label")) is not None:
            metric_names += [
                m.name for m in parse_expression(label[0], translated_metrics).metrics()
            ]
        return metric_names

    if perfometer["type"] == "logarithmic":
        return [
            m.name for m in parse_expression(perfometer["metric"], translated_metrics).metrics()
        ]

    if perfometer["type"] in ("stacked", "dual"):
        if "perfometers" not in perfometer:
            raise MKGeneralException(
                _("Perfometers of type 'stacked' and 'dual' need the element 'perfometers' (%r)")
                % perfometer
            )

        return [
            metric_name
            for sub_perfometer in perfometer["perfometers"]
            for metric_name in _get_metric_names(sub_perfometer, translated_metrics)
        ]
    raise NotImplementedError(_("Invalid perfometer type: %s") % perfometer["type"])


def _skip_perfometer_by_metric_names(
    perfometer: PerfometerSpec, translated_metrics: TranslatedMetrics
) -> bool:
    metric_names = set(_get_metric_names(perfometer, translated_metrics))
    available_metric_names = set(translated_metrics.keys())
    return not metric_names.issubset(available_metric_names)


def _total_values_exists(value: str | int | float, translated_metrics: TranslatedMetrics) -> bool:
    """
    Only if the value has a suffix like ':min'/':max' we need to check if the value actually exists in the scalar data
    The value could be a percentage value (e.g. '100.0') in this case no need to look here for missing data
    """
    if not isinstance(value, str):
        return True

    if ":" not in value:
        return True

    perf_name, perf_param = value.split(":", 1)
    if perf_param not in translated_metrics[perf_name]["scalar"].keys():
        return False

    return True


def _perfometer_possible(perfometer: PerfometerSpec, translated_metrics: TranslatedMetrics) -> bool:
    if not translated_metrics:
        return False

    if _skip_perfometer_by_metric_names(perfometer, translated_metrics):
        return False

    if perfometer["type"] == "linear":
        if "condition" in perfometer:
            try:
                return parse_conditional_expression(
                    perfometer["condition"], translated_metrics
                ).evaluate(translated_metrics)
            except Exception:
                return False

        if "total" in perfometer:
            return _total_values_exists(perfometer["total"], translated_metrics)

    return True


def get_first_matching_perfometer(translated_metrics: TranslatedMetrics) -> PerfometerSpec | None:
    for perfometer in perfometer_info:
        if not isinstance(perfometer, dict):
            continue
        if _perfometer_possible(perfometer, translated_metrics):
            return perfometer
    return None
