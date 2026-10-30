#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from cmk.graphing_engine._data._fetched import PerformanceData, value_of
from cmk.graphing_engine._data._naming import MetricName

from ._quantity_parsing import scalar_kind_of
from ._types import (
    ApiPerfometer,
    ApiScalar,
    metric_names_in_quantity,
    quantities_of_perfometer,
    scalars_in_quantity,
)


@dataclass(frozen=True, kw_only=True)
class _IndexedPerfometer:
    position: int
    name: str
    plugin: ApiPerfometer
    metric_names: frozenset[MetricName]
    scalars: Sequence[ApiScalar]


def _indexed(position: int, name: str, plugin: ApiPerfometer) -> _IndexedPerfometer:
    quantities = list(quantities_of_perfometer(plugin))
    return _IndexedPerfometer(
        position=position,
        name=name,
        plugin=plugin,
        metric_names=frozenset(
            metric_name
            for quantity in quantities
            for metric_name in metric_names_in_quantity(quantity)
        ),
        scalars=[scalar for quantity in quantities for scalar in scalars_in_quantity(quantity)],
    )


def _scalar_has_a_value(
    scalar: ApiScalar, performance_data: Mapping[MetricName, PerformanceData]
) -> bool:
    data = performance_data.get(MetricName(scalar.metric_name))
    return data is not None and value_of(data, scalar_kind_of(scalar)) is not None


def _matches(
    perfometer: _IndexedPerfometer, performance_data: Mapping[MetricName, PerformanceData]
) -> bool:
    return (
        bool(perfometer.metric_names)
        and perfometer.metric_names <= performance_data.keys()
        and all(_scalar_has_a_value(scalar, performance_data) for scalar in perfometer.scalars)
    )


class PerfometerIndex:
    def __init__(self, plugins: Mapping[str, ApiPerfometer]) -> None:
        self.plugins: Final = plugins
        self._by_name: Final = {
            name: _indexed(position, name, plugin)
            for position, (name, plugin) in enumerate(plugins.items())
        }
        by_metric_name: dict[MetricName, list[_IndexedPerfometer]] = {}
        for perfometer in self._by_name.values():
            for metric_name in perfometer.metric_names:
                by_metric_name.setdefault(metric_name, []).append(perfometer)
        self._by_metric_name: Final[Mapping[MetricName, Sequence[_IndexedPerfometer]]] = (
            by_metric_name
        )

    def first_match(
        self,
        performance_data: Mapping[MetricName, PerformanceData],
        superseders: Mapping[str, str],
    ) -> ApiPerfometer | None:
        candidates = {
            perfometer.position: perfometer
            for metric_name in performance_data
            for perfometer in self._by_metric_name.get(metric_name, ())
        }
        for position in sorted(candidates):
            perfometer = candidates[position]
            if not _matches(perfometer, performance_data):
                continue
            superseder_name = superseders.get(perfometer.name)
            superseder = None if superseder_name is None else self._by_name.get(superseder_name)
            if superseder is not None and _matches(superseder, performance_data):
                return superseder.plugin
            return perfometer.plugin
        return None
