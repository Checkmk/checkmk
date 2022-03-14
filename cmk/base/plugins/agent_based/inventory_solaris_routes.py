#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Sequence[Mapping[str, str]]


def parse_solaris_routes(string_table: StringTable) -> Section:
    return [route for line in string_table for route in (_parse_solaris_route(line),) if route]


def _parse_solaris_route(line: Sequence[str]) -> Mapping[str, str]:
    route = {}
    if len(line) >= 5 and not line[0].startswith("---") and line[0] != "Destination":

        route["target"] = _parse_network(line[0])
        route["gateway"] = line[1]
        if len(line) > 5:
            route["device"] = line[-1]

    return route


def _parse_network(network: str) -> str:
    if network == "default":
        return "0.0.0.0/0"
    return network


register.agent_section(
    name="solaris_routes",
    parse_function=parse_solaris_routes,
)


def inventory_solaris_routes(section: Section) -> InventoryResult:
    path = ["networking", "routes"]
    for route in section:
        yield TableRow(
            path=path,
            key_columns={
                "target": route["target"],
                "gateway": route["gateway"],
            },
            inventory_columns={
                "device": route.get("device"),
            },
            status_columns={},
        )


register.inventory_plugin(
    name="solaris_routes",
    inventory_function=inventory_solaris_routes,
)
