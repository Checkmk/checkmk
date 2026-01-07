#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.plugins.lib import interfaces
from cmk.plugins.netapp.agent_based.netapp_ontap_if import (
    _get_failover_home_port,
    _merge_if_counters_sections,
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


class TestMergeIfCountersSections:
    @pytest.fixture(autouse=True)
    def setup_sections(self) -> None:
        self.interfaces_section = {iface.name: iface for iface in INTERFACE_MODELS}
        self.ports_section = {port.item_name(): port for port in PORT_MODELS}
        self.counters_section = {counter.id: counter for counter in INTERFACE_COUNTERS}

    def test_merged_attributes(
        self,
    ) -> None:
        (interfaces_data, _) = _merge_if_counters_sections(
            self.interfaces_section, self.ports_section, self.counters_section, 0.0
        )

        assert interfaces_data[0].attributes == interfaces.Attributes(
            index="1",
            descr="lif1",
            alias="",
            type="6",
            speed=0,
            oper_status="1",
            out_qlen=None,
            phys_address="\x00\x0c)\x124V",
            oper_status_name="up",
            speed_as_text="",
            group=None,
            node=None,
            admin_status=None,
            extra_info=None,
        )
        assert interfaces_data[1].attributes == interfaces.Attributes(
            index="2",
            descr="lif2",
            alias="",
            type="6",
            speed=0,
            oper_status="2",
            out_qlen=None,
            phys_address="\x00\x0c)\x124W",
            oper_status_name="down",
            speed_as_text="",
            group=None,
            node=None,
            admin_status=None,
            extra_info=None,
        )
        assert interfaces_data[2].attributes == interfaces.Attributes(
            index="3",
            descr="lif3",
            alias="",
            type="6",
            speed=0,
            oper_status="1",
            out_qlen=None,
            phys_address="\x00\x0c)\x124X",
            oper_status_name="up",
            speed_as_text="",
            group=None,
            node=None,
            admin_status=None,
            extra_info=None,
        )

    def test_merged_counters(
        self,
    ) -> None:
        (interfaces_data, _) = _merge_if_counters_sections(
            self.interfaces_section, self.ports_section, self.counters_section, 0.0
        )

        assert interfaces_data[0].counters == interfaces.Counters(
            in_octets=1000000,
            in_mcast=0,
            in_bcast=None,
            in_nucast=None,
            in_ucast=10000,
            in_disc=None,
            in_err=5,
            out_octets=2000000,
            out_mcast=0,
            out_bcast=None,
            out_nucast=None,
            out_ucast=20000,
            out_disc=None,
            out_err=10,
        )
        assert interfaces_data[1].counters == interfaces.Counters(
            in_octets=500000,
            in_mcast=0,
            in_bcast=None,
            in_nucast=None,
            in_ucast=5000,
            in_disc=None,
            in_err=2,
            out_octets=1000000,
            out_mcast=0,
            out_bcast=None,
            out_nucast=None,
            out_ucast=10000,
            out_disc=None,
            out_err=3,
        )
        assert interfaces_data[2].counters == interfaces.Counters(
            in_octets=3000000,
            in_mcast=0,
            in_bcast=None,
            in_nucast=None,
            in_ucast=30000,
            in_disc=None,
            in_err=0,
            out_octets=4000000,
            out_mcast=0,
            out_bcast=None,
            out_nucast=None,
            out_ucast=40000,
            out_disc=None,
            out_err=1,
        )

    def test_merged_extra_data(
        self,
    ) -> None:
        (_, extra_data) = _merge_if_counters_sections(
            self.interfaces_section, self.ports_section, self.counters_section, 0.0
        )

        assert len(extra_data) == 3

        # do not check "lif1" because order is not guaranteed in a nested list
        assert extra_data["lif2"] == {
            "failover_policy": "home_port_only",
            "failover_ports": [{"node": "node1", "port": "a0a", "link-status": "down"}],
            "home_port": "a0a",
            "home_node": "node1",
            "is_home": False,
        }
        assert extra_data["lif3"] == {
            "failover_policy": "broadcast_domain_only",
            "failover_ports": [{"node": "node2", "port": "e0a-100", "link-status": "up"}],
            "home_port": "e0a-100",
            "home_node": "node2",
            "is_home": True,
        }

    def test_without_counters(
        self,
    ) -> None:
        (interfaces_data, _) = _merge_if_counters_sections(
            self.interfaces_section, self.ports_section, None, 0.0
        )

        # Should still work, but with no counter data
        assert (
            interfaces_data[0].counters
            == interfaces_data[1].counters
            == interfaces_data[2].counters
            == interfaces.Counters(
                in_octets=0,
                in_mcast=0,
                in_bcast=None,
                in_nucast=None,
                in_ucast=0,
                in_disc=None,
                in_err=0,
                out_octets=0,
                out_mcast=0,
                out_bcast=None,
                out_nucast=None,
                out_ucast=0,
                out_disc=None,
                out_err=0,
            )
        )
