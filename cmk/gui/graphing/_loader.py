#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass

from cmk.utils.plugin_registry import Registry

from cmk.gui.log import logger
from cmk.gui.valuespec import Age, Filesize, Float, Integer, Percentage

import cmk.ccc.debug
from cmk.discover_plugins import discover_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import entry_point_prefixes, graphs, metrics, perfometers, translations

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
    discovered_plugins: DiscoveredPlugins[
        metrics.Metric
        | translations.Translation
        | perfometers.Perfometer
        | perfometers.Bidirectional
        | perfometers.Stacked
        | graphs.Graph
        | graphs.Bidirectional
    ] = discover_plugins(
        PluginGroup.GRAPHING,
        entry_point_prefixes(),
        raise_errors=cmk.ccc.debug.enabled(),
    )
    for exc in discovered_plugins.errors:
        logger.error(exc)
    return discovered_plugins


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


@dataclass(frozen=True)
class RegisteredUnit:
    name: str
    symbol: str
    title: str
    description: str
    valuespec: type[Age] | type[Filesize] | type[Float] | type[Integer] | type[Percentage]


def registered_units() -> Sequence[RegisteredUnit]:
    return sorted(
        [
            RegisteredUnit(
                name,
                info["symbol"],
                info["title"],
                info.get("description", ""),
                info.get("valuespec", Float),
            )
            for (name, info) in unit_info.items()
        ]
        + [
            RegisteredUnit(
                name,
                info["symbol"],
                info["title"],
                "",
                info.get("valuespec", Float),
            )
            for (name, info) in units_from_api.items()
        ],
        key=lambda x: x.title,
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
