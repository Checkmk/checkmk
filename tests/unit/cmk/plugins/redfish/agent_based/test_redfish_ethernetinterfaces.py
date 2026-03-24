#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_ethernetinterfaces import (
    check_redfish_ethernetinterfaces,
    discovery_redfish_ethernetinterfaces,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple


def _make_eth_entry(
    port_id: str = "1",
    *,
    speed: int = 10000,
    link_status: str = "LinkUp",
    mac: str = "AA:BB:CC:DD:EE:FF",
    health: str = "OK",
    state: str = "Enabled",
) -> str:
    entry: dict[str, Any] = {
        "@odata.id": f"/redfish/v1/Systems/1/EthernetInterfaces/{port_id}",
        "@odata.type": "#EthernetInterface.v1_12_0.EthernetInterface",
        "Id": port_id,
        "SpeedMbps": speed,
        "LinkStatus": link_status,
        "MACAddress": mac,
        "Status": {"Health": health, "State": state},
    }
    return json.dumps(entry)


def _make_string_table(*entries: str) -> StringTable:
    return [[e] for e in entries]


def test_discovery_updown() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_eth_entry()))
    services = list(discovery_redfish_ethernetinterfaces({"state": "updown"}, parsed))
    assert len(services) == 1
    assert services[0].item == "1"
    assert services[0].parameters["discover_speed"] == 10000
    assert services[0].parameters["discover_link_status"] == "LinkUp"


def test_discovery_up_only_skips_down() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_eth_entry(link_status="LinkDown")))
    services = list(discovery_redfish_ethernetinterfaces({"state": "up"}, parsed))
    assert len(services) == 0


def test_check_no_changes() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_eth_entry()))
    params = {"discover_speed": 10000, "discover_link_status": "LinkUp"}
    results = list(check_redfish_ethernetinterfaces("1", params, parsed))
    assert results[0] == Result(state=State.OK, summary="Link: LinkUp")
    assert results[1] == Result(state=State.OK, summary="Speed: 10 Gbps")
    assert results[2] == Result(state=State.OK, summary="MAC: AA:BB:CC:DD:EE:FF")


def test_check_link_status_changed() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_eth_entry(link_status="LinkDown")))
    params = {"discover_speed": 10000, "discover_link_status": "LinkUp"}
    results = [
        r for r in check_redfish_ethernetinterfaces("1", params, parsed) if isinstance(r, Result)
    ]
    assert results[0].state == State.CRIT
    assert "changed from LinkUp" in results[0].summary


def test_check_speed_changed() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_eth_entry(speed=1000)))
    params = {"discover_speed": 10000, "discover_link_status": "LinkUp"}
    results = [
        r for r in check_redfish_ethernetinterfaces("1", params, parsed) if isinstance(r, Result)
    ]
    assert results[1].state == State.WARN
    assert "changed from" in results[1].summary


def test_check_item_not_found() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_eth_entry()))
    results = list(check_redfish_ethernetinterfaces("99", {}, parsed))
    assert results == []
