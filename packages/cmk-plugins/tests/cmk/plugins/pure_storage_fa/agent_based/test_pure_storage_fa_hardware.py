#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.pure_storage_fa.agent_based.pure_storage_fa_hardware import (
    check_ethernet_port,
    check_fan,
    check_fibre_channel_port,
    check_infiniband_port,
    check_storage_bay,
    Device,
    discover_ethernet_port,
    discover_fan,
    discover_fibre_channel_port,
    discover_infiniband_port,
    discover_storage_bay,
    Hardware,
    parse_hardware,
)

HARDWARE = Hardware(
    storage_bays={
        "SH0.BAY3": Device(
            name="SH0.BAY3", status="ok", type="drive_bay", details="Storage bay doing good."
        )
    },
    ethernet_ports={
        "CT0.ETH3": Device(
            name="CT0.ETH3", status="unknown", type="eth_port", details="Unknown state"
        ),
        "CT0.ETH4": Device(
            name="CT0.ETH4", status="not_installed", type="eth_port", details="Not installed"
        ),
    },
    fibre_channel_ports={
        "CT0.FC0": Device(name="CT0.FC0", status="critical", type="fc_port", details=None)
    },
    infiniband_ports={
        "CT0.IB0": Device(name="CT0.IB0", status="healthy", type="ib_port", details=None)
    },
    fans={
        "SH0.FAN0": Device(
            name="SH0.FAN0",
            status="identifying",
            type="cooling",
            details="Still identifying the device.",
        )
    },
)


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        pytest.param(
            [
                [
                    '{"continuation_token": null, "items": [{"details": "Storage bay doing good.", "identify_enabled": false, "index": 3, "model": null, "name": "SH0.BAY3", "serial": "PS-0T2OPQH0", "slot": null, "speed": null, "status": "ok", "temperature": null, "type": "drive_bay", "voltage": null},  {"details": "Still identifying the device.", "identify_enabled": null, "index": 0, "model": null, "name": "SH0.FAN0", "serial": null, "slot": null, "speed": null, "status": "identifying", "temperature": null, "type": "cooling", "voltage": null}, {"details": null, "identify_enabled": null, "index": 0, "model": null, "name": "CT0.FC0", "serial": null, "slot": 6, "speed": 8000000000, "status": "critical", "temperature": null, "type": "fc_port", "voltage": null}, {"details": null, "identify_enabled": null, "index": 0, "model": null, "name": "CT0.IB0", "serial": null, "slot": 4, "speed": 56000000000, "status": "healthy", "temperature": null, "type": "ib_port", "voltage": null}, {"details": null, "identify_enabled": null, "index": 0, "model": null, "name": "CT0.PWR0", "serial": null, "slot": null, "speed": null, "status": "ok", "temperature": null, "type": "power_supply", "voltage": null}, {"details": "Unknown state", "identify_enabled": null, "index": 3, "model": null, "name": "CT0.ETH3", "serial": null, "slot": null, "speed": 10000000000, "status": "unknown", "temperature": null, "type": "eth_port", "voltage": null}, {"details": "Not installed","identify_enabled": null,"index": 4,"model": null,"name": "CT0.ETH4","serial": null,"slot": null,"speed": 10000000000,"status": "not_installed","temperature": null,"type": "eth_port","voltage": null}], "more_items_remaining": false, "total_item_count": null}'
                ]
            ],
            HARDWARE,
            id="one hardware in section",
        ),
        pytest.param(
            [
                [
                    '{"continuation_token": null, "more_items_remaining": false, "total_item_count": null}'
                ]
            ],
            None,
            id="no hardware",
        ),
    ],
)
def test_parse_hardware(string_table: StringTable, expected_section: Hardware) -> None:
    assert parse_hardware(string_table) == expected_section


@pytest.mark.parametrize(
    "section, expected_services",
    [
        (
            HARDWARE,
            [Service(item="SH0.BAY3")],
        )
    ],
)
def test_discover_storage_bay(section: Hardware, expected_services: DiscoveryResult) -> None:
    assert list(discover_storage_bay(section)) == expected_services


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            HARDWARE,
            "SH0.BAY3",
            [
                Result(state=State.OK, summary="Status: ok"),
                Result(state=State.OK, summary="Storage bay doing good."),
            ],
            id="item present in section",
        ),
        pytest.param(
            HARDWARE,
            "Unknown",
            [],
            id="no item in section",
        ),
    ],
)
def test_check_storage_bay(
    section: Hardware,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert list(check_storage_bay(item, section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_services",
    [
        (
            HARDWARE,
            [Service(item="CT0.ETH3"), Service(item="CT0.ETH4")],
        )
    ],
)
def test_discover_ethernet_port(section: Hardware, expected_services: DiscoveryResult) -> None:
    assert list(discover_ethernet_port(section)) == expected_services


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            HARDWARE,
            "CT0.ETH3",
            [
                Result(state=State.WARN, summary="Status: unknown"),
                Result(state=State.OK, summary="Unknown state"),
            ],
            id="item present in section",
        ),
        pytest.param(
            HARDWARE,
            "Unknown",
            [],
            id="no item in section",
        ),
        pytest.param(
            HARDWARE,
            "CT0.ETH4",
            [
                Result(state=State.OK, summary="Status: not_installed"),
                Result(state=State.OK, summary="Not installed"),
            ],
            id="OK state for not installed",
        ),
    ],
)
def test_check_ethernet_port(
    section: Hardware,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert list(check_ethernet_port(item, section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_services",
    [
        (
            HARDWARE,
            [Service(item="CT0.FC0")],
        )
    ],
)
def test_discover_fibre_channel_port(section: Hardware, expected_services: DiscoveryResult) -> None:
    assert list(discover_fibre_channel_port(section)) == expected_services


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            HARDWARE,
            "CT0.FC0",
            [
                Result(state=State.CRIT, summary="Status: critical"),
            ],
            id="item present in section",
        ),
        pytest.param(
            HARDWARE,
            "Unknown",
            [],
            id="no item in section",
        ),
    ],
)
def test_check_fibre_channel_port(
    section: Hardware,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert list(check_fibre_channel_port(item, section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_services",
    [
        (
            HARDWARE,
            [Service(item="CT0.IB0")],
        )
    ],
)
def test_discover_infiniband_port(section: Hardware, expected_services: DiscoveryResult) -> None:
    assert list(discover_infiniband_port(section)) == expected_services


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            HARDWARE,
            "CT0.IB0",
            [
                Result(state=State.OK, summary="Status: healthy"),
            ],
            id="item present in section",
        ),
        pytest.param(
            HARDWARE,
            "Unknown",
            [],
            id="no item in section",
        ),
    ],
)
def test_check_infiniband_port(
    section: Hardware,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert list(check_infiniband_port(item, section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_services",
    [
        (
            HARDWARE,
            [Service(item="SH0.FAN0")],
        )
    ],
)
def test_discover_fan(section: Hardware, expected_services: DiscoveryResult) -> None:
    assert list(discover_fan(section)) == expected_services


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            HARDWARE,
            "SH0.FAN0",
            [
                Result(state=State.WARN, summary="Status: identifying"),
                Result(state=State.OK, summary="Still identifying the device."),
            ],
            id="item present in section",
        ),
        pytest.param(
            HARDWARE,
            "Unknown",
            [],
            id="no item in section",
        ),
    ],
)
def test_check_fan(
    section: Hardware,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert list(check_fan(item, section)) == expected_result
