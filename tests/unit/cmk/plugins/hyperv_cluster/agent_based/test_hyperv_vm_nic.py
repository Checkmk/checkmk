#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Example output from agent:
# <<<hyperv_vm_nic:cached(1750083965,120)>>>
# nic 1
# nic.name Network Adapter
# nic.id Microsoft:12345678-1234-1234-1234-123456789ABC\98765432-9876-9876-9876-987654321DEF
# nic.connectionstate True
# nic.vswitch Red Hat VirtIO Ethernet Adapter - Virtual Switch
# nic.dynamicMAC True
# nic.MAC 3E5A9C7F2B1D
# nic.IP 192.168.122.13
# nic.IP fe80::1a2b:3c4d:5e6f:7g8h
# nic.security.DHCPGuard Off
# nic.security.RouterGuard Off
# nic.VLAN.mode Untagged
# nic.VLAN.id 0

# <<<hyperv_vm_nic:cached(1758552026,90)>>>
# nic 2
# nic.name Test Adapter
# nic.id Microsoft:580018EF-56AC-4C1D-8A84-0F81608452B4\08B07A4C-A48D-49F5-A76C-BC976F5C0166
# nic.connectionstate True
# nic.vswitch InternalSwitch
# nic.dynamicMAC True
# nic.MAC 00155D030F01
# nic.IP not assigned
# nic.security.DHCPGuard Off
# nic.security.RouterGuard Off
# nic.VLAN.mode Untagged
# nic.VLAN.id 0
# nic.name Test Adapter
# nic.id Microsoft:580018EF-56AC-4C1D-8A84-0F81608452B4\C7BFAE54-D10B-4E21-9A77-60FE98B8772E
# nic.connectionstate True
# nic.vswitch InternalSwitch
# nic.dynamicMAC False
# nic.MAC 00155D030902
# nic.IP not assigned
# nic.security.DHCPGuard Off
# nic.security.RouterGuard Off
# nic.VLAN.mode Untagged
# nic.VLAN.id 0

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.hyperv_cluster.agent_based.hyperv_vm_nic import (
    check_hyperv_vm_nic,
    NicParams,
    parse_hyperv_vm_nic,
    Section,
)


def test_parse_empty_string_table() -> None:
    result = parse_hyperv_vm_nic([])
    assert result == {}


def test_parse_single_adapter() -> None:
    string_table: StringTable = [
        ["nic", "1"],
        ["nic.name", "Test", "Adapter"],
        [
            "nic.id",
            "Microsoft:580018EF-56AC-4C1D-8A84-0F81608452B4\\08B07A4C-A48D-49F5-A76C-BC976F5C0166",
        ],
        ["nic.connectionstate", "True"],
        ["nic.vswitch", "InternalSwitch"],
        ["nic.dynamicMAC", "True"],
        ["nic.MAC", "00155D030F01"],
        ["nic.IP", "not", "assigned"],
        ["nic.security.DHCPGuard", "Off"],
        ["nic.security.RouterGuard", "Off"],
        ["nic.VLAN.mode", "Untagged"],
        ["nic.VLAN.id", "0"],
    ]

    result = parse_hyperv_vm_nic(string_table)

    expected_key = "08B07A4C-A48D-49F5-A76C-BC976F5C0166"
    assert len(result) == 1
    assert expected_key in result

    adapter_data = result[expected_key]
    assert adapter_data["nic.name"] == "Test Adapter"
    assert (
        adapter_data["nic.id"]
        == "Microsoft:580018EF-56AC-4C1D-8A84-0F81608452B4\\08B07A4C-A48D-49F5-A76C-BC976F5C0166"
    )
    assert adapter_data["nic.connectionstate"] == "True"
    assert adapter_data["nic.vswitch"] == "InternalSwitch"
    assert adapter_data["nic.dynamicMAC"] == "True"
    assert adapter_data["nic.MAC"] == "00155D030F01"
    assert adapter_data["nic.IP"] == "not assigned"
    assert adapter_data["nic.security.DHCPGuard"] == "Off"
    assert adapter_data["nic.security.RouterGuard"] == "Off"
    assert adapter_data["nic.VLAN.mode"] == "Untagged"
    assert adapter_data["nic.VLAN.id"] == "0"


def test_parse_multiple_adapters() -> None:
    string_table: StringTable = [
        ["nic", "2"],
        ["nic.name", "Test", "Adapter"],
        [
            "nic.id",
            "Microsoft:580018EF-56AC-4C1D-8A84-0F81608452B4\\08B07A4C-A48D-49F5-A76C-BC976F5C0166",
        ],
        ["nic.connectionstate", "True"],
        ["nic.vswitch", "InternalSwitch"],
        ["nic.dynamicMAC", "True"],
        ["nic.MAC", "00155D030F01"],
        ["nic.IP", "not", "assigned"],
        ["nic.security.DHCPGuard", "Off"],
        ["nic.security.RouterGuard", "Off"],
        ["nic.VLAN.mode", "Untagged"],
        ["nic.VLAN.id", "0"],
        ["nic.name", "Test", "Adapter"],
        [
            "nic.id",
            "Microsoft:580018EF-56AC-4C1D-8A84-0F81608452B4\\C7BFAE54-D10B-4E21-9A77-60FE98B8772E",
        ],
        ["nic.connectionstate", "True"],
        ["nic.vswitch", "InternalSwitch"],
        ["nic.dynamicMAC", "False"],
        ["nic.MAC", "00155D030902"],
        ["nic.IP", "not", "assigned"],
        ["nic.security.DHCPGuard", "Off"],
        ["nic.security.RouterGuard", "Off"],
        ["nic.VLAN.mode", "Untagged"],
        ["nic.VLAN.id", "0"],
    ]

    result = parse_hyperv_vm_nic(string_table)

    assert len(result) == 2

    first_key = "08B07A4C-A48D-49F5-A76C-BC976F5C0166"
    second_key = "C7BFAE54-D10B-4E21-9A77-60FE98B8772E"

    assert first_key in result
    assert second_key in result

    first_adapter = result[first_key]
    assert first_adapter["nic.name"] == "Test Adapter"
    assert first_adapter["nic.dynamicMAC"] == "True"
    assert first_adapter["nic.MAC"] == "00155D030F01"

    second_adapter = result[second_key]
    assert second_adapter["nic.name"] == "Test Adapter"
    assert second_adapter["nic.dynamicMAC"] == "False"
    assert second_adapter["nic.MAC"] == "00155D030902"


def test_parse_nic_id_without_backslash() -> None:
    string_table: StringTable = [
        ["nic.name", "Simple", "Adapter"],
        ["nic.id", "SimpleID123"],
        ["nic.connectionstate", "True"],
    ]

    result = parse_hyperv_vm_nic(string_table)

    assert len(result) == 1
    assert "SimpleID123" in result
    assert result["SimpleID123"]["nic.name"] == "Simple Adapter"


def test_parse_multiword_values() -> None:
    string_table: StringTable = [
        ["nic.name", "Multi", "Word", "Adapter", "Name"],
        ["nic.id", "test-guid"],
        ["nic.IP", "192.168.1.100", "255.255.255.0", "gateway"],
    ]

    result = parse_hyperv_vm_nic(string_table)

    assert len(result) == 1
    assert "test-guid" in result
    assert result["test-guid"]["nic.name"] == "Multi Word Adapter Name"
    assert result["test-guid"]["nic.IP"] == "192.168.1.100 255.255.255.0 gateway"


def test_parse_skip_nic_lines() -> None:
    string_table: StringTable = [
        ["nic", "1"],
        ["nic", "some", "other", "data"],
        ["nic.name", "Test", "Adapter"],
        ["nic.id", "test-guid"],
        ["nic", "ignored"],
    ]

    result = parse_hyperv_vm_nic(string_table)

    assert len(result) == 1
    assert "test-guid" in result
    assert result["test-guid"]["nic.name"] == "Test Adapter"


@pytest.mark.parametrize(
    "item, section, params, expected_results",
    [
        # Test case: No parameters provided (default behavior)
        (
            "nic-guid-5",
            {
                "nic-guid-5": {
                    "nic.name": "Default Adapter",
                    "nic.connectionstate": "True",
                    "nic.vswitch": "DefaultSwitch",
                    "nic.dynamicMAC": "False",
                    "nic.VLAN.mode": "Tagged",
                    "nic.VLAN.id": "300",
                }
            },
            {},  # No parameters
            [
                ("Name: Default Adapter", State.OK),
                ("Connected: True", State.OK),
                ("Dynamic MAC: False", State.OK),
                ("Virtual switch: DefaultSwitch", State.OK),
                ("VLAN mode: Tagged", State.OK),
                ("VLAN ID: 300", State.OK),
            ],
        ),
        # Test case: Partial parameters provided
        (
            "nic-guid-6",
            {
                "nic-guid-6": {
                    "nic.name": "Partial Adapter",
                    "nic.connectionstate": "False",
                    "nic.vswitch": "PartialSwitch",
                    "nic.dynamicMAC": "True",
                    "nic.VLAN.mode": "Untagged",
                    "nic.VLAN.id": "0",
                }
            },
            {
                "connection_state": {
                    "connected": "true",
                    "state_if_not_expected": State.CRIT.value,
                },
                # Only connection_state param provided
            },
            [
                ("Name: Partial Adapter", State.OK),
                ("Connected: False", State.CRIT),
                ("Dynamic MAC: True", State.OK),
                ("Virtual switch: PartialSwitch", State.OK),
                ("VLAN mode: Untagged", State.OK),
                ("VLAN ID: 0", State.OK),
            ],
        ),
        # Test case: NIC with "Unknown NIC" name
        (
            "nic-guid-7",
            {
                "nic-guid-7": {
                    # Missing nic.name
                    "nic.connectionstate": "True",
                    "nic.vswitch": "TestSwitch",
                    "nic.dynamicMAC": "True",
                    "nic.VLAN.mode": "Untagged",
                    "nic.VLAN.id": "0",
                }
            },
            {},
            [
                ("Name: Unknown NIC", State.OK),
                ("Connected: True", State.OK),
                ("Dynamic MAC: True", State.OK),
                ("Virtual switch: TestSwitch", State.OK),
                ("VLAN mode: Untagged", State.OK),
                ("VLAN ID: 0", State.OK),
            ],
        ),
        # Test case: Empty vswitch name in parameters
        (
            "nic-guid-8",
            {
                "nic-guid-8": {
                    "nic.name": "Empty Switch Adapter",
                    "nic.connectionstate": "True",
                    "nic.vswitch": "",
                    "nic.dynamicMAC": "True",
                    "nic.VLAN.mode": "Untagged",
                    "nic.VLAN.id": "0",
                }
            },
            {
                "expected_vswitch": {
                    "name": "",
                    "state_if_not_expected": State.WARN.value,
                },
            },
            [
                ("Name: Empty Switch Adapter", State.OK),
                ("Connected: True", State.OK),
                ("Dynamic MAC: True", State.OK),
                ("Virtual switch: ", State.OK),
                ("VLAN mode: Untagged", State.OK),
                ("VLAN ID: 0", State.OK),
            ],
        ),
        # Test case: All fields unknown/missing with parameters
        (
            "nic-guid-9",
            {
                "nic-guid-9": {
                    "nic.name": "Missing Fields Adapter",
                    # All other fields missing
                }
            },
            {
                "connection_state": {
                    "connected": "true",
                    "state_if_not_expected": State.CRIT.value,
                },
                "dynamic_mac": {
                    "dynamic_mac_enabled": "false",
                    "state_if_not_expected": State.CRIT.value,
                },
                "expected_vswitch": {
                    "name": "ExpectedSwitch",
                    "state_if_not_expected": State.CRIT.value,
                },
            },
            [
                ("Name: Missing Fields Adapter", State.OK),
                ("Connection state missing for NIC: nic-guid-9", State.UNKNOWN),
                ("Dynamic MAC missing for NIC: nic-guid-9", State.UNKNOWN),
                ("Virtual switch missing for NIC: nic-guid-9", State.UNKNOWN),
                ("VLAN mode missing for NIC: nic-guid-9", State.WARN),
                ("VLAN ID missing for NIC: nic-guid-9", State.WARN),
            ],
        ),
        # Test case: Case sensitivity test for connection state
        (
            "nic-guid-10",
            {
                "nic-guid-10": {
                    "nic.name": "Case Test Adapter",
                    "nic.connectionstate": "TRUE",  # Uppercase
                    "nic.vswitch": "CaseSwitch",
                    "nic.dynamicMAC": "FALSE",  # Uppercase
                    "nic.VLAN.mode": "Tagged",
                    "nic.VLAN.id": "400",
                }
            },
            {
                "connection_state": {
                    "connected": "true",  # Lowercase expected
                    "state_if_not_expected": State.WARN.value,
                },
                "dynamic_mac": {
                    "dynamic_mac_enabled": "false",  # Lowercase expected
                    "state_if_not_expected": State.WARN.value,
                },
            },
            [
                ("Name: Case Test Adapter", State.OK),
                ("Connected: TRUE", State.OK),  # Case insensitive comparison
                ("Dynamic MAC: FALSE", State.OK),  # Case insensitive comparison
                ("Virtual switch: CaseSwitch", State.OK),
                ("VLAN mode: Tagged", State.OK),
                ("VLAN ID: 400", State.OK),
            ],
        ),
        # Test case: Different state levels for mismatches
        (
            "nic-guid-11",
            {
                "nic-guid-11": {
                    "nic.name": "State Level Adapter",
                    "nic.connectionstate": "False",
                    "nic.vswitch": "WrongSwitch",
                    "nic.dynamicMAC": "False",
                    "nic.VLAN.mode": "Tagged",
                    "nic.VLAN.id": "500",
                }
            },
            {
                "connection_state": {
                    "connected": "true",
                    "state_if_not_expected": State.CRIT.value,
                },
                "dynamic_mac": {
                    "dynamic_mac_enabled": "true",
                    "state_if_not_expected": State.UNKNOWN.value,
                },
                "expected_vswitch": {
                    "name": "ExpectedSwitch",
                    "state_if_not_expected": State.OK.value,
                },
            },
            [
                ("Name: State Level Adapter", State.OK),
                ("Connected: False", State.CRIT),
                ("Dynamic MAC: False", State.UNKNOWN),
                ("Virtual switch: WrongSwitch", State.OK),
                ("VLAN mode: Tagged", State.OK),
                ("VLAN ID: 500", State.OK),
            ],
        ),
    ],
)
def test_check_hyperv_vm_nic_additional_cases(item, section, params, expected_results):
    results = list(check_hyperv_vm_nic(item, params, section))
    assert len(results) == len(expected_results)
    for result, (expected_summary, expected_state) in zip(results, expected_results):
        assert isinstance(result, Result)
        assert result.summary == expected_summary
        assert result.state == expected_state


def test_check_hyperv_vm_nic_empty_section():
    empty_section: Section = {}
    params: NicParams = {
        "connection_state": {
            "connected": "true",
            "state_if_not_expected": State.WARN.value,
        }
    }

    results = list(check_hyperv_vm_nic("nonexistent-nic", params, empty_section))
    assert len(results) == 1
    assert isinstance(results[0], Result)
    assert results[0].summary == "NIC information is missing: nonexistent-nic"
    assert results[0].state == State.WARN


def test_check_hyperv_vm_nic_with_default_params():
    from cmk.plugins.hyperv_cluster.agent_based.hyperv_vm_nic import hyperv_vm_nic_default_params

    section: Section = {
        "test-nic": {
            "nic.name": "Test Default Params",
            "nic.connectionstate": "False",
            "nic.vswitch": "WrongSwitch",
            "nic.dynamicMAC": "False",
            "nic.VLAN.mode": "Tagged",
            "nic.VLAN.id": "100",
        }
    }

    results = list(check_hyperv_vm_nic("test-nic", hyperv_vm_nic_default_params, section))
    assert len(results) == 6

    assert isinstance(results[0], Result)
    assert results[0].summary == "Name: Test Default Params"
    assert results[0].state == State.OK

    assert isinstance(results[1], Result)
    assert "Connected: False" in results[1].summary
    assert results[1].state == State.WARN

    assert isinstance(results[2], Result)
    assert "Dynamic MAC: False" in results[2].summary
    assert results[2].state == State.OK

    assert isinstance(results[3], Result)
    assert "Virtual switch: WrongSwitch" in results[3].summary
    assert results[3].state == State.OK


def test_check_hyperv_vm_nic_field_variations():
    section: Section = {
        "variation-nic": {
            "nic.name": "Variation Adapter",
            "nic.connectionstate": "unknown",
            "nic.vswitch": "unknown",
            "nic.dynamicMAC": "unknown",
            "nic.VLAN.mode": "no VLAN mode",
            "nic.VLAN.id": "no VLAN ID",
        }
    }

    params: NicParams = {
        "connection_state": {
            "connected": "true",
            "state_if_not_expected": State.WARN.value,
        },
        "dynamic_mac": {
            "dynamic_mac_enabled": "true",
            "state_if_not_expected": State.WARN.value,
        },
        "expected_vswitch": {
            "name": "ExpectedSwitch",
            "state_if_not_expected": State.WARN.value,
        },
    }

    results = list(check_hyperv_vm_nic("variation-nic", params, section))
    assert len(results) == 6

    # Should get UNKNOWN states for unknown values
    assert isinstance(results[1], Result)
    assert results[1].state == State.UNKNOWN
    assert "Connection state missing" in results[1].summary

    assert isinstance(results[2], Result)
    assert results[2].state == State.UNKNOWN
    assert "Dynamic MAC missing" in results[2].summary

    assert isinstance(results[3], Result)
    assert results[3].state == State.UNKNOWN
    assert "Virtual switch missing" in results[3].summary

    # VLAN fields should be WARN for missing values
    assert isinstance(results[4], Result)
    assert results[4].state == State.WARN
    assert "VLAN mode missing" in results[4].summary

    assert isinstance(results[5], Result)
    assert results[5].state == State.WARN
    assert "VLAN ID missing" in results[5].summary
