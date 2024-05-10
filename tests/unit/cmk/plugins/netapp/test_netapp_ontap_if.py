#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.plugins.netapp.agent_based.netapp_ontap_if import (
    _get_failover_home_port,
    _merge_if_counters_sections,
    _merge_interface_port,
)
from cmk.plugins.netapp.models import InterfaceCounters, IpInterfaceModel, PortModel


class InterfaceCountersFactory(ModelFactory):
    __model__ = InterfaceCounters


class IpInterfaceModelFactory(ModelFactory):
    __model__ = IpInterfaceModel


class PortModelFactory(ModelFactory):
    __model__ = PortModel


_PORT_MODELS = [
    PortModelFactory.build(
        port_type="physical",
        node_name="node_name",
        name="port1",
        state="up",
        speed=100,
        mac_address="00:00:00:00:00:00",
    ),
    PortModelFactory.build(
        port_type="lag",
        node_name="node_name",
        name="port2",
        state="down",
        speed=100,
        mac_address="01:00:00:00:00:00",
    ),
]

_INTERFACE_MODELS = [
    IpInterfaceModelFactory.build(
        name="interface1",
        uuid="uuid1",
        state="up",
        enabled=True,
        node_name="node_name",
        port_name="port1",
        failover="alert_failover",
        home_node="node_name",
        home_port="port1",
        is_home=True,
    ),
    IpInterfaceModelFactory.build(
        name="interface2",
        uuid="uuid1",
        state="up",
        enabled=True,
        node_name="node_name",
        port_name="port2",
        failover="home_port_only",
        home_node="node_name",
        home_port="port2",
        is_home=False,
    ),
]

_INTERFACE_COUNTERS_MODELS = [
    InterfaceCountersFactory.build(
        # id composition: node_name:interface_name:??
        id="node_name:interface1:random",
        recv_data=100,
        recv_packet=100,
        recv_errors=100,
        send_data=100,
        send_packet=100,
        send_errors=100,
    ),
    InterfaceCountersFactory.build(
        # id composition: node_name:interface_name:??
        id="node_name:interface2:random",
        recv_data=200,
        recv_packet=200,
        recv_errors=200,
        send_data=200,
        send_packet=200,
        send_errors=200,
    ),
]


@pytest.mark.parametrize(
    "interface, expected_result",
    [
        pytest.param(
            IpInterfaceModelFactory.build(
                home_node="node_name",
                home_port="port1",
            ),
            "node_name|port1|up",
            id="matching port-interface",
        ),
        pytest.param(
            IpInterfaceModelFactory.build(
                home_node="node_name_not_matching",
                home_port="port1",
            ),
            None,
            id="no maching port-interface",
        ),
    ],
)
def test_get_failover_home_port(
    interface: IpInterfaceModel,
    expected_result: str | None,
) -> None:
    interface_values = interface.serialize()
    ports_section = {port_model.item_name(): port_model for port_model in _PORT_MODELS}

    result = _get_failover_home_port(ports_section, interface_values)
    assert result == expected_result


@pytest.mark.parametrize(
    "interface, added_info",
    [
        pytest.param(
            IpInterfaceModelFactory.build(
                node_name="node_name",
                port_name="port1",
            ),
            _PORT_MODELS[0].serialize(),
            id="matching port-interface",
        ),
        pytest.param(
            IpInterfaceModelFactory.build(
                node_name="node_name_not_matching",
                port_name="port1",
            ),
            {},
            id="no maching port-interface",
        ),
    ],
)
def test_merge_interface_port(interface: IpInterfaceModel, added_info: dict) -> None:
    interface_values = interface.serialize()
    ports_section = {port_model.item_name(): port_model for port_model in _PORT_MODELS}

    result = _merge_interface_port(ports_section, interface_values)
    assert result == (interface_values | added_info)


def test_merge_if_counters_sections() -> None:
    ports_section = {port_model.item_name(): port_model for port_model in _PORT_MODELS}
    interfaces_section = {interface.name: interface for interface in _INTERFACE_MODELS}
    interfaces_counters_section = {
        if_counter.id: if_counter for if_counter in _INTERFACE_COUNTERS_MODELS
    }

    result = _merge_if_counters_sections(
        interfaces_section, ports_section, interfaces_counters_section
    )

    assert result[0][0][0].attributes.oper_status_name == "up"
    assert result[0][0][0].attributes.oper_status == "1"
    assert result[0][0][1].attributes.oper_status_name == "down"
    assert result[0][0][1].attributes.oper_status == "2"

    assert result[0][0][0].counters.in_octets == 100
    assert result[0][0][0].counters.in_ucast == 100

    assert result[0][0][1].counters.in_octets == 200
    assert result[0][0][1].counters.in_ucast == 200

    assert result[0][1]["interface1"]["is_home"] is True
    assert result[0][1]["interface1"]["home_port"] == "port1"
    assert "failover_ports" not in result[0][1]["interface1"]

    assert result[0][1]["interface2"]["is_home"] is False
    assert result[0][1]["interface2"]["home_port"] == "port2"
    assert result[0][1]["interface2"]["failover_ports"] == [
        {"node": "node_name", "port": "port2", "link-status": "down"}
    ]
