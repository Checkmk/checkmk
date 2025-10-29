#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.plugins.netapp.agent_based.netapp_ontap_if import (
    _get_failover_home_port,
    _merge_interface_counters,
    _merge_interface_port,
    parse_netapp_interfaces,
    parse_netapp_interfaces_counters,
)
from cmk.plugins.netapp.models import InterfaceCounters, IpInterfaceModel, PortModel


class InterfaceCountersFactory(ModelFactory):
    __model__ = InterfaceCounters


class IpInterfaceModelFactory(ModelFactory):
    __model__ = IpInterfaceModel


class PortModelFactory(ModelFactory):
    __model__ = PortModel


PORT_MODELS = [
    PortModelFactory.build(
        port_type="physical",
        uuid="uuid-physical",
        node_name="node1",
        name="e0a",
        state="up",
        speed=1000,
        mac_address="00:0c:29:12:34:56",
        broadcast_domain="Default",
    ),
    PortModelFactory.build(
        port_type="lag",
        uuid="uuid-lag",
        node_name="node1",
        name="a0a",
        state="down",
        speed=2000,
        mac_address="00:0c:29:12:34:57",
        broadcast_domain="Default",
    ),
    PortModelFactory.build(
        port_type="vlan",
        uuid="uuid-vlan",
        node_name="node2",
        name="e0a-100",
        state="up",
        speed=1000,
        mac_address="00:0c:29:12:34:58",
        broadcast_domain="VLAN100",
    ),
]


INTERFACE_MODELS = [
    IpInterfaceModelFactory.build(
        name="lif1",
        uuid="uuid-lif1",
        state="up",
        enabled=True,
        node_name="node1",
        port_name="e0a",
        failover="default",
        home_node="node1",
        home_port="e0a",
        is_home=True,
    ),
    IpInterfaceModelFactory.build(
        name="lif2",
        uuid="uuid-lif2",
        state="down",
        enabled=True,
        node_name="node1",
        port_name="a0a",
        failover="home_port_only",
        home_node="node1",
        home_port="a0a",
        is_home=False,
    ),
    IpInterfaceModelFactory.build(
        name="lif3",
        uuid="uuid-lif3",
        state="up",
        enabled=True,
        node_name="node2",
        port_name="e0a-100",
        failover="broadcast_domain_only",
        home_node="node2",
        home_port="e0a-100",
        is_home=True,
    ),
]


INTERFACE_COUNTERS = [
    InterfaceCountersFactory.build(
        id="node1:lif1:12345",
        recv_data=1000000,
        recv_packet=10000,
        recv_errors=5,
        send_data=2000000,
        send_packet=20000,
        send_errors=10,
    ),
    InterfaceCountersFactory.build(
        id="node1:lif2:12346",
        recv_data=500000,
        recv_packet=5000,
        recv_errors=2,
        send_data=1000000,
        send_packet=10000,
        send_errors=3,
    ),
    InterfaceCountersFactory.build(
        id="node2:lif3:12347",
        recv_data=3000000,
        recv_packet=30000,
        recv_errors=0,
        send_data=4000000,
        send_packet=40000,
        send_errors=1,
    ),
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [
                [
                    '{"name": "lif1", "uuid": "uuid1", "state": "up", "enabled": true, '
                    '"node_name": "node1", "port_name": "e0a", "failover": "default", '
                    '"home_node": "node1", "home_port": "e0a", "is_home": true}'
                ]
            ],
            {
                "lif1": IpInterfaceModel(
                    name="lif1",
                    uuid="uuid1",
                    state="up",
                    enabled=True,
                    node_name="node1",
                    port_name="e0a",
                    failover="default",
                    home_node="node1",
                    home_port="e0a",
                    is_home=True,
                ),
            },
            id="Single interface",
        ),
        pytest.param(
            [
                [
                    '{"name": "lif1", "uuid": "uuid1", "state": "up", "enabled": true, '
                    '"node_name": "node1", "port_name": "e0a", "failover": "default", '
                    '"home_node": "node1", "home_port": "e0a", "is_home": true}'
                ],
                [
                    '{"name": "lif2", "uuid": "uuid2", "state": "down", "enabled": true, '
                    '"node_name": "node1", "port_name": "e0b", "failover": "default", '
                    '"home_node": "node1", "home_port": "e0b", "is_home": false}'
                ],
            ],
            {
                "lif1": IpInterfaceModel(
                    name="lif1",
                    uuid="uuid1",
                    state="up",
                    enabled=True,
                    node_name="node1",
                    port_name="e0a",
                    failover="default",
                    home_node="node1",
                    home_port="e0a",
                    is_home=True,
                ),
                "lif2": IpInterfaceModel(
                    name="lif2",
                    uuid="uuid2",
                    state="down",
                    enabled=True,
                    node_name="node1",
                    port_name="e0b",
                    failover="default",
                    home_node="node1",
                    home_port="e0b",
                    is_home=False,
                ),
            },
            id="Multiple interfaces",
        ),
        pytest.param([], {}, id="Empty input"),
    ],
)
def test_parse_netapp_interfaces(
    string_table: list[list[str]], expected_result: Mapping[str, IpInterfaceModel]
) -> None:
    assert parse_netapp_interfaces(string_table) == expected_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [
                [
                    '{"id": "node1:lif1:12345", "recv_data": 1000, "recv_packet": 100, '
                    '"recv_errors": 1, "send_data": 2000, "send_packet": 200, "send_errors": 2}'
                ]
            ],
            {
                "node1:lif1:12345": InterfaceCounters(
                    id="node1:lif1:12345",
                    recv_data=1000,
                    recv_packet=100,
                    recv_errors=1,
                    send_data=2000,
                    send_packet=200,
                    send_errors=2,
                )
            },
            id="Single Counter",
        ),
        pytest.param(
            [
                [
                    '{"id": "node1:lif1:12345", "recv_data": 1000, "recv_packet": 100, '
                    '"recv_errors": 1, "send_data": 2000, "send_packet": 200, "send_errors": 2}'
                ],
                [
                    '{"id": "node1:lif2:12346", "recv_data": 3000, "recv_packet": 300, '
                    '"recv_errors": 3, "send_data": 4000, "send_packet": 400, "send_errors": 4}'
                ],
            ],
            {
                "node1:lif1:12345": InterfaceCounters(
                    id="node1:lif1:12345",
                    recv_data=1000,
                    recv_packet=100,
                    recv_errors=1,
                    send_data=2000,
                    send_packet=200,
                    send_errors=2,
                ),
                "node1:lif2:12346": InterfaceCounters(
                    id="node1:lif2:12346",
                    recv_data=3000,
                    recv_packet=300,
                    recv_errors=3,
                    send_data=4000,
                    send_packet=400,
                    send_errors=4,
                ),
            },
            id="Multiple Counters",
        ),
        pytest.param([], {}, id="Emtpy"),
    ],
)
def test_parse_netapp_interfaces_counters(
    string_table: list[list[str]], expected_result: Mapping[str, InterfaceCounters]
) -> None:
    assert parse_netapp_interfaces_counters(string_table) == expected_result


@pytest.mark.parametrize(
    "home_node, home_port, expected_result",
    [
        pytest.param("node1", "e0a", "node1|e0a|up", id="physical port up"),
        pytest.param("node1", "a0a", "node1|a0a|down", id="lag port down"),
        pytest.param("node_invalid", "e0a", None, id="invalid node"),
        pytest.param("node1", "invalid_port", None, id="invalid port"),
        pytest.param("node_invalid", "invalid_port", None, id="invalid node and port"),
    ],
)
def test_get_failover_home_port(
    home_node: str,
    home_port: str,
    expected_result: str | None,
) -> None:
    interface_values = {"home-node": home_node, "home-port": home_port}
    ports_section = {port.item_name(): port for port in PORT_MODELS}

    result = _get_failover_home_port(ports_section, interface_values)
    assert result == expected_result


@pytest.mark.parametrize(
    "node_name, port_name, expected_result",
    [
        pytest.param(
            "node1",
            "e0a",
            {
                "node_name": "node1",
                "port-node": "node1",
                "port-uuid": "uuid-physical",
                "port_name": "e0a",
                "port_state": "up",
                "port-name": "e0a",
                "port_type": "physical",
                "speed": 1000,
                "mac-address": "00:0c:29:12:34:56",
                "broadcast_domain": "Default",
            },
            id="matching physical port",
        ),
        pytest.param(
            "node1",
            "a0a",
            {
                "node_name": "node1",
                "port-node": "node1",
                "port-uuid": "uuid-lag",
                "port_name": "a0a",
                "port_state": "down",
                "port-name": "a0a",
                "port_type": "lag",
                "speed": 2000,
                "mac-address": "00:0c:29:12:34:57",
                "broadcast_domain": "Default",
            },
            id="matching lag port",
        ),
    ],
)
def test_merge_interface_port(
    node_name: str,
    port_name: str,
    expected_result: dict,
) -> None:
    interface_values = {"node_name": node_name, "port_name": port_name}
    ports_section = {port.item_name(): port for port in PORT_MODELS}

    result = _merge_interface_port(ports_section, interface_values)
    assert result == expected_result


@pytest.mark.parametrize(
    "counters, expected_result",
    [
        pytest.param(
            INTERFACE_COUNTERS[0],
            {
                "name": "test_interface",
                "state": "up",
                "id": "node1:lif1:12345",
                "recv_data": 1000000,
                "recv_packet": 10000,
                "recv_errors": 5,
                "send_data": 2000000,
                "send_packet": 20000,
                "send_errors": 10,
            },
            id="Counters",
        ),
        pytest.param(
            None,
            {"name": "test_interface", "state": "up"},
            id="No Counters",
        ),
    ],
)
def test_merge_interface_counters(
    counters: InterfaceCounters, expected_result: Mapping[str, str]
) -> None:
    interface_dict = {"name": "test_interface", "state": "up"}
    assert _merge_interface_counters(counters, interface_dict) == expected_result
