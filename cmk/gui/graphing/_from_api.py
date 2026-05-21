#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from typing import assert_never

from cmk.ccc.plugin_registry import Registry
from cmk.gui.color import parse_color_from_api
from cmk.gui.unit_formatter import AutoPrecision, StrictPrecision

from ._api_types import graphs_v1, metrics_v1, perfometers_v1
from ._unit import (
    ConvertibleUnitSpecification,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    SINotation,
    StandardScientificNotation,
    TimeNotation,
)


@dataclass(frozen=True)
class RegisteredMetric:
    name: str
    title_localizer: Callable[[Callable[[str], str]], str]
    unit_spec: ConvertibleUnitSpecification
    color: str


def parse_metric_from_api(metric_from_api: metrics_v1.Metric) -> RegisteredMetric:
    return RegisteredMetric(
        name=metric_from_api.name,
        title_localizer=metric_from_api.title.localize,
        unit_spec=parse_unit_from_api(metric_from_api.unit),
        color=parse_color_from_api(metric_from_api.color).value,
    )


def parse_unit_from_api(unit_from_api: metrics_v1.Unit) -> ConvertibleUnitSpecification:
    notation: (
        DecimalNotation
        | SINotation
        | IECNotation
        | StandardScientificNotation
        | EngineeringScientificNotation
        | TimeNotation
    )
    match unit_from_api.notation:
        case metrics_v1.DecimalNotation(symbol):
            notation = DecimalNotation(symbol=symbol)
        case metrics_v1.SINotation(symbol):
            notation = SINotation(symbol=symbol)
        case metrics_v1.IECNotation(symbol):
            notation = IECNotation(symbol=symbol)
        case metrics_v1.StandardScientificNotation(symbol):
            notation = StandardScientificNotation(symbol=symbol)
        case metrics_v1.EngineeringScientificNotation(symbol):
            notation = EngineeringScientificNotation(symbol=symbol)
        case metrics_v1.TimeNotation():
            notation = TimeNotation(symbol=unit_from_api.notation.symbol)
        case _:
            assert_never(unit_from_api.notation)

    precision: AutoPrecision | StrictPrecision
    match unit_from_api.precision:
        case metrics_v1.AutoPrecision(digits):
            precision = AutoPrecision(digits=digits)
        case metrics_v1.StrictPrecision(digits):
            precision = StrictPrecision(digits=digits)
        case _:
            assert_never(unit_from_api.precision)

    return ConvertibleUnitSpecification(
        notation=notation,
        precision=precision,
    )


class MetricsFromAPI(Registry[RegisteredMetric]):
    def plugin_name(self, instance: RegisteredMetric) -> str:
        return instance.name


metrics_from_api = MetricsFromAPI()


class PerfometersFromAPI(
    Registry[perfometers_v1.Perfometer | perfometers_v1.Bidirectional | perfometers_v1.Stacked]
):
    def plugin_name(
        self,
        instance: (
            perfometers_v1.Perfometer | perfometers_v1.Bidirectional | perfometers_v1.Stacked
        ),
    ) -> str:
        return instance.name


perfometers_from_api = PerfometersFromAPI()


class GraphsFromAPI(Registry[graphs_v1.Graph | graphs_v1.Bidirectional]):
    def plugin_name(self, instance: graphs_v1.Graph | graphs_v1.Bidirectional) -> str:
        return instance.name


graphs_from_api = GraphsFromAPI()
