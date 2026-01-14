#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Result, State, TableRow
from cmk.plugins.netapp.agent_based.netapp_ontap_info import (
    check_netapp_ontap_info,
    inventorize_netapp_ontap_info,
)
from cmk.plugins.netapp.models import NodeModel, Version


class NodeModelFactory(ModelFactory):
    __model__ = NodeModel


class VersionFactory(ModelFactory):
    __model__ = Version


def test_check_netapp_ontap_info() -> None:
    node_model = NodeModelFactory.build(
        version=VersionFactory.build(
            full="Release Full string description",  # eg: "NetApp Release 9.12.1P6: Fri Aug 04 00:26:53 UTC 2023"
        ),
    )
    section = {node_model.name: node_model}

    result = list(check_netapp_ontap_info(node_model.name, section))

    assert result == [Result(state=State.OK, summary="Version: Release Full string description")]


def test_inventorize_netapp_ontap_info() -> None:
    node_models = [
        NodeModelFactory.build(
            namne="Node 1 name",
            model="Model 1",
            system_machine_type="System machine type 1",
            serial_number="Serial number 1",
            system_id="System id 1",
            cpu_count=36,
            cpu_processor="Cpu rocessor 1",
        ),
        NodeModelFactory.build(
            namne="Node 2 name",
            model="Model 2",
            system_machine_type="System machine type 2",
            serial_number="Serial number 2",
            system_id="System id 2",
            cpu_count=36,
            cpu_processor="Cpu rocessor 2",
        ),
    ]
    section = {node_model.name: node_model for node_model in node_models}

    result = list(inventorize_netapp_ontap_info(section))

    assert isinstance(result[0], TableRow)
    assert result[0].inventory_columns == {"cores": 36, "model": "Cpu rocessor 1"}
    assert isinstance(result[1], TableRow)
    assert result[1].inventory_columns == {
        "model": "Model 1",
        "product": "System machine type 1",
        "serial": "Serial number 1",
        "id": "System id 1",
    }
