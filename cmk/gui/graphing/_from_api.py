#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from cmk.ccc.plugin_registry import Registry
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import perfometers as perfometers_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import perfometers as perfometers_v2_unstable
from cmk.graphing_engine import parse_unit, Unit
from cmk.gui.color import parse_color_from_api


@dataclass(frozen=True)
class RegisteredMetric:
    name: str
    title_localizer: Callable[[Callable[[str], str]], str]
    unit: Unit
    color: str


def parse_metric_from_api(metric_from_api: metrics_v1.Metric) -> RegisteredMetric:
    return RegisteredMetric(
        name=metric_from_api.name,
        title_localizer=metric_from_api.title.localize,
        unit=parse_unit(metric_from_api.unit),
        color=parse_color_from_api(metric_from_api.color).value,
    )


class MetricsFromAPI(Registry[RegisteredMetric]):
    @override
    def plugin_name(self, instance: RegisteredMetric) -> str:
        return instance.name


metrics_from_api = MetricsFromAPI()


type PerfometerFromAPI = (
    perfometers_v1.Perfometer
    | perfometers_v1.Bidirectional
    | perfometers_v1.Stacked
    | perfometers_v2_unstable.Perfometer
    | perfometers_v2_unstable.Bidirectional
    | perfometers_v2_unstable.Stacked
)


class PerfometersFromAPI(Registry[PerfometerFromAPI]):
    @override
    def plugin_name(self, instance: PerfometerFromAPI) -> str:
        return instance.name


perfometers_from_api = PerfometersFromAPI()


type GraphFromAPI = (
    graphs_v1.Graph
    | graphs_v1.Bidirectional
    | graphs_v2_unstable.Graph
    | graphs_v2_unstable.Bidirectional
)


class GraphsFromAPI(Registry[GraphFromAPI]):
    @override
    def plugin_name(self, instance: GraphFromAPI) -> str:
        return instance.name


graphs_from_api = GraphsFromAPI()
