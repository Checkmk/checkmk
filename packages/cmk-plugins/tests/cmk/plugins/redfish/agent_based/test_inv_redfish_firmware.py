#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable, TableRow
from cmk.plugins.redfish.agent_based.inv_redfish_firmware import (
    check_redfish_firmware,
    discovery_redfish_firmware,
    inventorize_redfish_firmware,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple, RedfishAPIData

_PATH = ["hardware", "firmware", "redfish"]


def _firmware_section(*entries: Mapping[str, object]) -> RedfishAPIData:
    string_table: StringTable = [
        [json.dumps({"@odata.type": "#SoftwareInventory.v1_2_0.SoftwareInventory", **entry})]
        for entry in entries
    ]
    return parse_redfish_multiple(string_table)


def _summaries(section: RedfishAPIData) -> list[tuple[State, str]]:
    return [
        (result.state, result.summary)
        for result in check_redfish_firmware(section)
        if isinstance(result, Result)
    ]


def test_firmware_service_is_discovered_if_there_is_firmware() -> None:
    section = _firmware_section({"Id": "BMC", "Name": "BMC"})

    assert list(discovery_redfish_firmware(section)) == [Service()]


def test_firmware_service_is_not_discovered_without_firmware() -> None:
    assert list(discovery_redfish_firmware(_firmware_section())) == []


def test_firmware_in_optimal_state_is_ok() -> None:
    section = _firmware_section(
        {"Id": "BMC", "Name": "BMC", "Status": {"Health": "OK", "State": "Enabled"}},
        {"Id": "BIOS", "Name": "BIOS", "Status": {"Health": "OK", "State": "Enabled"}},
    )

    assert _summaries(section) == [(State.OK, "All firmware in optimal state")]


def test_critical_firmware_makes_the_service_crit() -> None:
    section = _firmware_section(
        {"Id": "1", "Name": "BIOS", "Status": {"Health": "Critical", "State": "Enabled"}}
    )

    assert _summaries(section) == [
        (
            State.CRIT,
            (
                "1-BIOS - Component State: A critical condition requires immediate attention., "
                "This resource is enabled. - "
            ),
        )
    ]


@pytest.mark.parametrize(
    "state",
    [
        pytest.param("Disabled", id="disabled"),
        pytest.param("StandbyOffline", id="standby offline"),
    ],
)
def test_firmware_that_is_not_active_is_ok(state: str) -> None:
    section = _firmware_section(
        {"Id": "BIOS", "Name": "BIOS", "Status": {"Health": "Critical", "State": state}}
    )

    assert _summaries(section) == [(State.OK, "All firmware in optimal state")]


def test_firmware_without_status_is_not_in_the_details() -> None:
    section = _firmware_section(
        {"Id": "BMC", "Name": "BMC", "Status": {"Health": "OK"}},
        {"Id": "BIOS", "Name": "BIOS"},
    )

    (result,) = check_redfish_firmware(section)

    assert isinstance(result, Result)
    assert "BMC" in result.details
    assert "BIOS" not in result.details


def test_firmware_is_inventorized_with_version_description_and_updateability() -> None:
    section = _firmware_section(
        {
            "Id": "BMC",
            "Name": "Integrated BMC",
            "Version": "1.20",
            "Description": "Baseboard management firmware",
            "Updateable": True,
        }
    )

    assert list(inventorize_redfish_firmware(section)) == [
        TableRow(
            path=_PATH,
            key_columns={"component": "BMC-Integrated BMC"},
            inventory_columns={
                "version": "1.20",
                "description": "Baseboard management firmware",
                "updateable": True,
            },
        )
    ]


def test_firmware_inventory_entry_is_described_by_its_id() -> None:
    # iDRAC style: every entry carries the same generic description
    section = _firmware_section(
        {
            "Id": "Installed-25227-6.10.30.20__NIC.Embedded.1-1-1",
            "Name": "Broadcom Gigabit Ethernet BCM5720",
            "Version": "6.10.30.20",
            "Description": "Represents Firmware Inventory",
            "Updateable": True,
        }
    )

    assert list(inventorize_redfish_firmware(section)) == [
        TableRow(
            path=_PATH,
            key_columns={"component": "Installed-Broadcom Gigabit Ethernet BCM5720"},
            inventory_columns={
                "version": "6.10.30.20",
                "description": "Installed-25227-6.10.30.20__NIC.Embedded.1-1-1",
                "updateable": True,
            },
        )
    ]


@pytest.mark.parametrize(
    "entry, component",
    [
        pytest.param({"Id": "BIOS", "Name": "BIOS"}, "BIOS", id="id equals name"),
        pytest.param({"Name": "BIOS"}, "BIOS", id="name without id"),
        pytest.param({"Id": "7", "Name": "BIOS"}, "7-BIOS", id="numeric id"),
    ],
)
def test_firmware_component_is_named_after_id_and_name(
    entry: dict[str, str], component: str
) -> None:
    rows = inventorize_redfish_firmware(_firmware_section(entry))

    assert [row.key_columns["component"] for row in rows if isinstance(row, TableRow)] == [
        component
    ]


def test_numeric_firmware_ids_are_zero_padded() -> None:
    section = _firmware_section(*({"Id": str(i), "Name": f"FW{i}"} for i in range(1, 11)))

    rows = inventorize_redfish_firmware(section)

    assert [row.key_columns["component"] for row in rows if isinstance(row, TableRow)] == [
        "01-FW1",
        "02-FW2",
        "03-FW3",
        "04-FW4",
        "05-FW5",
        "06-FW6",
        "07-FW7",
        "08-FW8",
        "09-FW9",
        "10-FW10",
    ]


def test_firmware_without_id_and_name_is_not_inventorized() -> None:
    section = _firmware_section({"Version": "1.0"})

    assert list(inventorize_redfish_firmware(section)) == []


def test_hp_firmware_inventory_is_inventorized_from_its_current_versions() -> None:
    # iLO 4 answers with one resource listing the current version of every component
    section = _firmware_section(
        {
            "@odata.type": "#FwSwVersionInventory.1.2.0.FwSwVersionInventory",
            "Id": "FirmwareInventory",
            "Current": {
                "SystemRomActive": [
                    {
                        "Name": "System ROM",
                        "VersionString": "P89 v2.76 (10/21/2019)",
                        "Location": "System Board",
                    }
                ],
                "SystemBMC": [
                    {"Name": "iLO", "VersionString": "2.80 Jan 25 2022", "Location": "System Board"}
                ],
            },
        }
    )

    assert list(inventorize_redfish_firmware(section)) == [
        TableRow(
            path=_PATH,
            key_columns={"component": "0-System ROM"},
            inventory_columns={"version": "P89 v2.76 (10/21/2019)", "location": "System Board"},
        ),
        TableRow(
            path=_PATH,
            key_columns={"component": "1-iLO"},
            inventory_columns={"version": "2.80 Jan 25 2022", "location": "System Board"},
        ),
    ]
