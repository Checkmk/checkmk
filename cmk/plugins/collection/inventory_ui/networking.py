#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_alpha import (
    DecimalNotation,
    Label,
    Node,
    NumberField,
    StrictPrecision,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))


def _render_ip_address_type(value: str) -> Label | str:
    match value:
        case "ipv4":
            return "IPv4"
        case "ipv6":
            return "IPv6"
        case _:
            return value


def _render_ipv4_network(value: str) -> Label | str:
    return Label("Default") if value == "0.0.0.0/0" else value


def _render_route_type(value: str) -> Label | str:
    return Label("Local route") if value == "local" else Label("Gateway route")


node_networking = Node(
    name="networking",
    path=["networking"],
    title=Title("Networking"),
    attributes={
        "hostname": TextField(Title("Host name")),
        "total_interfaces": NumberField(Title("Total interfaces"), render=UNIT_COUNT),
        "total_ethernet_ports": NumberField(Title("Ports"), render=UNIT_COUNT),
        "available_ethernet_ports": NumberField(Title("Ports available"), render=UNIT_COUNT),
    },
)

node_networking_addresses = Node(
    name="networking_addresses",
    path=["networking", "addresses"],
    title=Title("IP addresses"),
    table=Table(
        columns={
            "address": TextField(Title("Address")),
            "device": TextField(Title("Device")),
            "type": TextField(Title("Address type"), render=_render_ip_address_type),
        },
    ),
)

node_networking_kube = Node(
    name="networking_kube",
    path=["networking", "kube"],
    title=Title("Kubernetes"),
    table=Table(
        columns={
            "ip": TextField(Title("IP address")),
            "address_type": TextField(Title("Type")),
        },
    ),
)

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

node_networking_sip_interfaces = Node(
    name="networking_sip_interfaces",
    path=["networking", "sip_interfaces"],
    title=Title("SIP Interfaces"),
    table=Table(
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "application_type": TextField(Title("Application Type")),
            "sys_interface": TextField(Title("System Interface")),
            "device": TextField(Title("Device")),
            "tcp_port": TextField(Title("TCP Port")),
            "gateway": TextField(Title("Gateway")),
        },
    ),
)

node_networking_tunnels = Node(
    name="networking_tunnels",
    path=["networking", "tunnels"],
    title=Title("Networking tunnels"),
    table=Table(
        view=View(name="invtunnels", title=Title("Networking tunnels")),
        columns={
            "peername": TextField(Title("Peer name")),
            "index": TextField(Title("Index")),
            "peerip": TextField(Title("Peer IP address")),
            "sourceip": TextField(Title("Source IP address")),
            "tunnelinterface": TextField(Title("Tunnel interface")),
            "linkpriority": TextField(Title("Link priority")),
        },
    ),
)

node_networking_wlan = Node(
    name="networking_wlan",
    path=["networking", "wlan"],
    title=Title("WLAN"),
)

node_networking_wlan_controller = Node(
    name="networking_wlan_controller",
    path=["networking", "wlan", "controller"],
    title=Title("Controller"),
)
