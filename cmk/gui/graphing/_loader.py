#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import cmk.utils.debug
from cmk.utils.plugin_registry import Registry

from cmk.discover_plugins import discover_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import graphs, metrics, perfometers, translations

from ._type_defs import UnitInfo
from ._unit_info import unit_info


def load_graphing_plugins() -> (
    DiscoveredPlugins[
        metrics.Metric
        | translations.Translation
        | perfometers.Perfometer
        | perfometers.Bidirectional
        | perfometers.Stacked
        | graphs.Graph
        | graphs.Bidirectional
    ]
):
    return discover_plugins(
        PluginGroup.GRAPHING,
        {
            metrics.Metric: "metric_",
            translations.Translation: "translation_",
            perfometers.Perfometer: "perfometer_",
            perfometers.Bidirectional: "perfometer_",
            perfometers.Stacked: "perfometer_",
            graphs.Graph: "graph_",
            graphs.Bidirectional: "graph_",
        },
        raise_errors=cmk.utils.debug.enabled(),
    )


class UnitsFromAPI(Registry[UnitInfo]):
    def plugin_name(self, instance: UnitInfo) -> str:
        return instance["id"]


units_from_api = UnitsFromAPI()


def get_unit_info(unit_id: str) -> UnitInfo:
    if unit_id in units_from_api:
        return units_from_api[unit_id]
    if unit_id in unit_info.keys():
        return unit_info[unit_id]
    return unit_info[""]


def registered_units() -> Sequence[tuple[str, str]]:
    return sorted(
        [(name, info.get("description", info["title"])) for (name, info) in unit_info.items()]
        + [(unit_id, info["symbol"]) for (unit_id, info) in units_from_api.items()],
        key=lambda x: x[1],
    )


class PerfometersFromAPI(
    Registry[perfometers.Perfometer | perfometers.Bidirectional | perfometers.Stacked]
):
    def plugin_name(
        self, instance: perfometers.Perfometer | perfometers.Bidirectional | perfometers.Stacked
    ) -> str:
        return instance.name


perfometers_from_api = PerfometersFromAPI()


class GraphsFromAPI(Registry[graphs.Graph | graphs.Bidirectional]):
    def plugin_name(self, instance: graphs.Graph | graphs.Bidirectional) -> str:
        return instance.name


graphs_from_api = GraphsFromAPI()
