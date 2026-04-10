#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Attributes
from cmk.plugins.apc.agent_based.inventory_apc_netshelterpdu import (
    APCNetShelterPDUInventory,
    inventorize_apc_netshelterpdu,
    parse_apc_netshelterpdu_inventory,
)


def test_parse_inventory() -> None:
    section = parse_apc_netshelterpdu_inventory(
        [
            [
                [
                    "346-415V, 63A, 43.5kVA, 50/60Hz",
                    "APDU10450SM",
                    "XX0000Y00000",
                    "2024/01/15 12:00:00",
                    "3.0.0",
                ]
            ],
            [["my-test-apdu", "DC1 Room2"]],
        ]
    )
    assert section == APCNetShelterPDUInventory(
        model="APDU10450SM",
        serial_number="XX0000Y00000",
        firmware_version="3.0.0",
        manufacture_date="2024/01/15 12:00:00",
        electrical_rating="346-415V, 63A, 43.5kVA, 50/60Hz",
        system_name="my-test-apdu",
        location="DC1 Room2",
    )


def test_parse_inventory_empty() -> None:
    assert parse_apc_netshelterpdu_inventory([[], []]) is None


def test_parse_inventory_no_sys_info() -> None:
    section = parse_apc_netshelterpdu_inventory(
        [
            [["346-415V", "APDU10450SM", "SN123", "2025/01/01", "3.0.0"]],
            [],
        ]
    )
    assert section is not None
    assert section.system_name == ""
    assert section.location == ""


def test_inventorize() -> None:
    section = APCNetShelterPDUInventory(
        model="APDU10450SM",
        serial_number="XX0000Y00000",
        firmware_version="3.0.0",
        manufacture_date="2024/01/15 12:00:00",
        electrical_rating="346-415V, 63A, 43.5kVA, 50/60Hz",
        system_name="my-test-apdu",
        location="DC1 Room2",
    )
    result = list(inventorize_apc_netshelterpdu(section))
    assert (
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "manufacturer": "APC",
                "model": "APDU10450SM",
                "serial": "XX0000Y00000",
                "manufacture_date": "2024/01/15 12:00:00",
                "electrical_rating": "346-415V, 63A, 43.5kVA, 50/60Hz",
            },
        )
        in result
    )
    assert (
        Attributes(
            path=["software", "firmware"],
            inventory_attributes={
                "vendor": "APC",
                "version": "3.0.0",
            },
        )
        in result
    )
    assert (
        Attributes(
            path=["networking"],
            inventory_attributes={
                "hostname": "my-test-apdu",
                "location": "DC1 Room2",
            },
        )
        in result
    )


def test_inventorize_empty_location() -> None:
    section = APCNetShelterPDUInventory(
        model="APDU10450SM",
        serial_number="SN123",
        firmware_version="3.0.0",
        manufacture_date="2025/01/01",
        electrical_rating="346-415V",
        system_name="mypdu",
        location="",
    )
    result = list(inventorize_apc_netshelterpdu(section))
    networking = next(a for a in result if isinstance(a, Attributes) and a.path == ["networking"])
    assert "location" not in networking.inventory_attributes
    assert networking.inventory_attributes["hostname"] == "mypdu"


def test_inventorize_no_networking_when_both_empty() -> None:
    section = APCNetShelterPDUInventory(
        model="APDU10450SM",
        serial_number="SN123",
        firmware_version="3.0.0",
        manufacture_date="2025/01/01",
        electrical_rating="346-415V",
        system_name="",
        location="",
    )
    result = list(inventorize_apc_netshelterpdu(section))
    assert not any(isinstance(a, Attributes) and a.path == ["networking"] for a in result)
