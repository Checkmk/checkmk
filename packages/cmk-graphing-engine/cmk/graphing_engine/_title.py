#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from collections.abc import Callable, Mapping

from ._objects import MetricName, RRDMetricData, ServiceRef

_TITLE_EXPRESSION_PREFIX = "_EXPRESSION:"
_TITLE_EXPRESSION_PATTERN = re.compile(re.escape(_TITLE_EXPRESSION_PREFIX) + r"\{.*?\}")
_TITLE_SCALARS: Mapping[str, Callable[[RRDMetricData], float | None]] = {
    "warn": lambda metric_data: metric_data.warning,
    "crit": lambda metric_data: metric_data.critical,
    "warn_lower": lambda metric_data: metric_data.lower_warning,
    "crit_lower": lambda metric_data: metric_data.lower_critical,
    "min": lambda metric_data: metric_data.minimum,
    "max": lambda metric_data: metric_data.maximum,
}


def _parse_title_expression(raw: str) -> Mapping[str, str]:
    expression: Mapping[str, str] = json.loads(raw[len(_TITLE_EXPRESSION_PREFIX) :])
    return expression


def _evaluate_title_expression(
    raw: str,
    translated_metrics: Mapping[MetricName, RRDMetricData],
) -> float | None:
    expression = _parse_title_expression(raw)
    if (translated := translated_metrics.get(MetricName(expression["metric"]))) is None:
        return None
    if (scalar := _TITLE_SCALARS.get(expression["scalar"])) is None:
        return None
    return scalar(translated)


def _flatten(
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
) -> Mapping[MetricName, RRDMetricData]:
    return {
        name: data
        for per_service in translated_metrics.values()
        for name, data in per_service.items()
    }


def evaluate_title(
    title: str,
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
) -> str:
    flattened = _flatten(translated_metrics)
    for raw in _TITLE_EXPRESSION_PATTERN.findall(title):
        value = _evaluate_title_expression(raw, flattened)
        if value is None:
            return title.split("-", maxsplit=1)[0].strip()
        title = title.replace(raw, str(int(value)), 1)
    return title
