#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State
from cmk.plugins.netapp.agent_based.netapp_ontap_ports import (
    check_netapp_ontap_ports,
    discover_netapp_ontap_ports,
)
from cmk.plugins.netapp.models import PortModel


class PortModelFactory(ModelFactory):
    __model__ = PortModel


_PORT_MODELS = [
    PortModelFactory.build(
        port_type="lag", node_name="node_name", name="port1", state="up", speed=100
    ),
    PortModelFactory.build(
        port_type="vlan", node_name="node_name", name="port2", state="down", speed=200
    ),
    PortModelFactory.build(
        port_type="physical",
        node_name="node_name",
        name="port3",
        speed=None,
        state="degraded",
    ),
]


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {"ignored_ports": []},
            [
                Service(item="Lag port node_name.port1"),
                Service(item="Physical port node_name.port3"),
            ],
            id="discovery all ports but down",
        ),
        pytest.param(
            {"ignored_ports": ["vlan", "physical"]},
            [
                Service(item="Lag port node_name.port1"),
            ],
            id="do not discover physical and vlan ports",
        ),
    ],
)
def test_discover_netapp_ontap_ports(
    params: Mapping[str, Any], expected_result: DiscoveryResult
) -> None:
    section = {port_model.item_name(): port_model for port_model in _PORT_MODELS}

    result = list(discover_netapp_ontap_ports(params, section))

    assert result == expected_result


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "Lag port node_name.port1",
            [
                Result(state=State.OK, summary="Health status: healthy"),
                Result(state=State.OK, summary="Operational speed: 100"),
            ],
            id="port is up",
        ),
        pytest.param(
            "Vlan port node_name.port2",
            [
                Result(state=State.UNKNOWN, summary="Health status: unknown"),
                Result(state=State.OK, summary="Operational speed: 200"),
            ],
            id="port is down",
        ),
        pytest.param(
            "Physical port node_name.port3",
            [
                Result(state=State.CRIT, summary="Health status: not healthy"),
                Result(state=State.OK, summary="Operational speed: undetermined"),
            ],
            id="port is degraded",
        ),
    ],
)
def test_check_netapp_ontap_ports(item: str, expected_result: CheckResult) -> None:
    section = {port_model.item_name(): port_model for port_model in _PORT_MODELS}

    result = list(check_netapp_ontap_ports(item, section))

    assert result == expected_result
