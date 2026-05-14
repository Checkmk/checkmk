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
    View,
)


def _render_ipv4_network(value: str) -> Label | str:
    return Label("Default") if value == "0.0.0.0/0" else value


def _render_route_type(value: str) -> Label | str:
    return Label("Local route") if value == "local" else Label("Gateway route")


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
    title=Title("SIP interfaces"),
    table=Table(
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "application_type": TextField(Title("Application Type")),
            "sys_interface": TextField(Title("System interface")),
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

node_networking_wlan_controller_accesspoints = Node(
    name="networking_wlan_controller_accesspoints",
    path=["networking", "wlan", "controller", "accesspoints"],
    title=Title("Access points"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "group": TextField(Title("Group")),
            "ip_addr": TextField(Title("IP address")),
            "model": TextField(Title("Model")),
            "serial": TextField(Title("Serial number")),
            "sys_location": TextField(Title("System location")),
        },
    ),
)


node_networking_device_uplinks = Node(
    name="networking_device_uplinks",
    path=["networking", "uplinks"],
    title=Title("Device uplinks"),
    table=Table(
        view=View(name="invdeviceuplinks", title=Title("Device uplinks")),
        columns={
            "interface": TextField(Title("Interface")),
            "protocol": TextField(Title("Protocol")),
            "address": TextField(Title("Address")),
            "gateway": TextField(Title("Gateway")),
            "public_address": TextField(Title("Public address")),
            "assignment_mode": TextField(Title("Assignment mode")),
        },
    ),
)
