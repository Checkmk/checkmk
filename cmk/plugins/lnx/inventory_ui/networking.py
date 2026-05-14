#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    Label,
    Node,
    Table,
    TextField,
    Title,
)


def _render_ipv4_network(value: str) -> Label | str:
    return Label("Default") if value == "0.0.0.0/0" else value


def _render_route_type(value: str) -> Label | str:
    return Label("Local route") if value == "local" else Label("Gateway route")


node_networking_routes = Node(
    name="networking_routes",
    path=["networking", "routes"],
    title=Title("Routes"),
    table=Table(
        columns={
            "target": TextField(Title("Target"), render=_render_ipv4_network),
            "device": TextField(Title("Device")),
            "type": TextField(Title("Type of route"), render=_render_route_type),
            "gateway": TextField(Title("Gateway")),
        },
    ),
)
