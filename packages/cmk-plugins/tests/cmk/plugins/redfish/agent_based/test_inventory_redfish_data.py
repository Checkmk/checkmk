#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import InventoryResult, StringTable, TableRow
from cmk.plugins.redfish.agent_based.inventory_redfish_data import inventorize_redfish_data
from cmk.plugins.redfish.lib import parse_redfish_multiple, RedfishAPIData

_ONLY_MANUFACTURER_INTEL = {
    "name": "Processor",
    "serial": "nothing set",
    "part_number": "nothing set",
    "manufacturer": "Intel",
    "model": "nothing set",
}


def _section(*entries: Mapping[str, object]) -> RedfishAPIData:
    string_table: StringTable = [[json.dumps(entry)] for entry in entries]
    return parse_redfish_multiple(string_table)


def _processor(odata_id: str, **fields: object) -> dict[str, object]:
    return {
        "@odata.id": odata_id,
        "@odata.type": "#Processor.v1_0_0.Processor",
        "Id": odata_id.rsplit("/", 1)[-1],
        "Name": "Processor",
        **fields,
    }


def _inventorize(
    processors: RedfishAPIData | None = None, power: RedfishAPIData | None = None
) -> InventoryResult:
    return inventorize_redfish_data(
        section_redfish_storage=None,
        section_redfish_processors=processors,
        section_redfish_drives=None,
        section_redfish_memory=None,
        section_redfish_power=power,
        section_redfish_thermal=None,
        section_redfish_networkadapters=None,
    )


def test_component_is_inventorized_below_its_redfish_path() -> None:
    processor = _processor(
        "/redfish/v1/Systems/1/Processors/CPU1",
        SerialNumber="SN123",
        PartNumber="P02499-001",
        Manufacturer="Intel(R) Corporation",
        Model="Intel(R) Xeon(R) Gold 6230",
    )

    assert list(_inventorize(processors=_section(processor))) == [
        TableRow(
            path=["hardware", "Systems", "1", "Processors"],
            key_columns={"id": "CPU1"},
            inventory_columns={
                "name": "Processor",
                "serial": "SN123",
                "part_number": "P02499-001",
                "manufacturer": "Intel(R) Corporation",
                "model": "Intel(R) Xeon(R) Gold 6230",
            },
        )
    ]


def test_missing_component_fields_are_marked_and_present_ones_stripped() -> None:
    processor = _processor("/redfish/v1/Systems/1/Processors/CPU1", Manufacturer=" Intel ")

    assert list(_inventorize(processors=_section(processor))) == [
        TableRow(
            path=["hardware", "Systems", "1", "Processors"],
            key_columns={"id": "CPU1"},
            inventory_columns=_ONLY_MANUFACTURER_INTEL,
        )
    ]


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({}, id="no identifying data"),
        pytest.param(
            {"SerialNumber": "NOT AVAILABLE", "PartNumber": "NOT AVAILABLE"},
            id="serial and part number not available",
        ),
    ],
)
def test_components_without_identifying_data_are_not_inventorized(
    fields: Mapping[str, object],
) -> None:
    processor = _processor("/redfish/v1/Systems/1/Processors/CPU1", **fields)

    assert list(_inventorize(processors=_section(processor))) == []


def test_components_outside_the_redfish_tree_are_not_inventorized() -> None:
    processor = _processor("/v1/Systems/1/Processors/CPU1", Manufacturer="Intel")

    assert list(_inventorize(processors=_section(processor))) == []


def test_oem_resources_are_not_inventorized() -> None:
    processor = _processor(
        "/redfish/v1/Systems/1/Processors/CPU1",
        Manufacturer="Intel",
        Oem={
            "Vendor": {
                "@odata.id": "/redfish/v1/Systems/1/Processors/CPU1/Oem/Vendor",
                "Name": "Vendor Processor Extension",
                "Manufacturer": "Vendor",
            }
        },
    )

    assert list(_inventorize(processors=_section(processor))) == [
        TableRow(
            path=["hardware", "Systems", "1", "Processors"],
            key_columns={"id": "CPU1"},
            inventory_columns=_ONLY_MANUFACTURER_INTEL,
        )
    ]


def test_dots_in_redfish_ids_become_underscores() -> None:
    processor = _processor(
        "/redfish/v1/Systems/System.Embedded.1/Processors/CPU.Socket.1", Manufacturer="Intel"
    )

    assert list(_inventorize(processors=_section(processor))) == [
        TableRow(
            path=["hardware", "Systems", "System_Embedded_1", "Processors"],
            key_columns={"id": "CPU_Socket_1"},
            inventory_columns=_ONLY_MANUFACTURER_INTEL,
        )
    ]


def test_components_nested_in_a_resource_are_inventorized() -> None:
    power = {
        "@odata.id": "/redfish/v1/Chassis/1/Power",
        "@odata.type": "#Power.v1_5_0.Power",
        "Id": "Power",
        "Name": "Power",
        "PowerSupplies": [
            {
                "@odata.id": "/redfish/v1/Chassis/1/Power#/PowerSupplies/0",
                "Name": "PS1",
                "SerialNumber": "5WBXK0FLLD",
                "Manufacturer": "Chicony",
            }
        ],
    }

    assert list(_inventorize(power=_section(power))) == [
        TableRow(
            path=["hardware", "Chassis", "1", "Power", "PowerSupplies"],
            key_columns={"id": "0"},
            inventory_columns={
                "name": "PS1",
                "serial": "5WBXK0FLLD",
                "part_number": "nothing set",
                "manufacturer": "Chicony",
                "model": "nothing set",
            },
        )
    ]
