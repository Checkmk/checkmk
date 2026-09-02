#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from collections.abc import Iterable, Iterator, Mapping

from ._fetched import ScalarKind
from ._naming import Service
from ._quantities import rrd_metric_of, RRDMetric, ScalarOf
from ._quantity import (
    EvaluationContext,
    first_value,
    MetricProtocol,
    QuantityProtocol,
)

_TITLE_EXPRESSION_PREFIX = "_EXPRESSION:"
_TITLE_EXPRESSION_PATTERN = re.compile(re.escape(_TITLE_EXPRESSION_PREFIX) + r"\{.*?\}")
_TITLE_SCALAR_KINDS: Mapping[str, ScalarKind] = {
    "warn": ScalarKind.WARNING,
    "crit": ScalarKind.CRITICAL,
    "warn_lower": ScalarKind.LOWER_WARNING,
    "crit_lower": ScalarKind.LOWER_CRITICAL,
    "min": ScalarKind.MINIMUM,
    "max": ScalarKind.MAXIMUM,
}


def _unique_service(metrics: Iterable[MetricProtocol]) -> Service | None:
    services = {metric.service() for metric in metrics if isinstance(metric, RRDMetric)}
    return next(iter(services)) if len(services) == 1 else None


def _title_quantity(raw: str, service: Service) -> QuantityProtocol | None:
    expression: Mapping[str, str] = json.loads(raw[len(_TITLE_EXPRESSION_PREFIX) :])
    metric = rrd_metric_of(service, expression["metric"])
    if (scalar := expression.get("scalar")) is None:
        return metric
    if (scalar_kind := _TITLE_SCALAR_KINDS.get(scalar)) is None:
        return None
    return ScalarOf(metric=metric, scalar_kind=scalar_kind)


def title_metrics(title: str, drawn_metrics: Iterable[MetricProtocol]) -> Iterator[MetricProtocol]:
    if (service := _unique_service(drawn_metrics)) is None:
        return
    for raw in _TITLE_EXPRESSION_PATTERN.findall(title):
        if (quantity := _title_quantity(raw, service)) is not None:
            yield from quantity.metrics()


def _fallback_title(title: str) -> str:
    return title.split("-", maxsplit=1)[0].strip()


def evaluate_title(
    title: str,
    drawn_metrics: Iterable[MetricProtocol],
    context: EvaluationContext,
) -> str:
    service = _unique_service(drawn_metrics)
    for raw in _TITLE_EXPRESSION_PATTERN.findall(title):
        if service is None or (quantity := _title_quantity(raw, service)) is None:
            return _fallback_title(title)
        value = first_value(quantity.evaluate(context))
        if value is None:
            return _fallback_title(title)
        title = title.replace(raw, str(int(value)), 1)
    return title
