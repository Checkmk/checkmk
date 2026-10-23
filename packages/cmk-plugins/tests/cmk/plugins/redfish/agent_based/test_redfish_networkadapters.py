#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_networkadapters import (
    check_redfish_networkadapters,
    discovery_redfish_networkadapters,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple, RedfishAPIData

_USED_MAC = "5c:ed:8c:04:7c:b8"
_UNUSED_MAC = "5c:ed:8c:04:7c:b9"


def _make_port(
    name: str | None, mac: str | None, *, link_up: bool, down_health: str = "Warning"
) -> dict[str, object]:
    port: dict[str, object] = (
        {"LinkStatus": "LinkUp", "Status": {"Health": "OK"}}
        if link_up
        else {
            "LinkStatus": "LinkDown",
            "Status": {"Health": down_health, "State": "UnavailableOffline"},
        }
    )
    if name is not None:
        port["Name"] = name
    if mac is not None:
        port["MacAddress"] = mac
    return port


def _make_adapter(
    *ports: dict[str, object],
    health: str = "Warning",
    with_ports: bool = True,
    null_ports: bool = False,
) -> RedfishAPIData:
    entry: dict[str, object] = {
        "@odata.id": "/redfish/v1/Systems/1/BaseNetworkAdapters/1",
        "@odata.type": "#HpeBaseNetworkAdapter.v2_0_0.HpeBaseNetworkAdapter",
        "Id": "1",
        "Name": "Marvell 2P 10GbE 10GBASE-T QL41132HQRJ-HC OCP3 Adapter",
        "PartNumber": "AH2010415-30  C",
        "SerialNumber": "REE2227P38647",
        "Status": {"Health": health, "State": "Enabled"},
    }
    if with_ports:
        entry["PhysicalPorts"] = None if null_ports else list(ports)
    string_table: StringTable = [[json.dumps(entry)]]
    return parse_redfish_multiple(string_table)


def _worst_state(item_params: Mapping[str, Sequence[str]], section: RedfishAPIData) -> State:
    return State.worst(
        *(
            r.state
            for r in check_redfish_networkadapters("1", item_params, section)
            if isinstance(r, Result)
        )
    )


def test_discovery_saves_only_linkup_ports() -> None:
    section = _make_adapter(
        _make_port("ens10f1", _UNUSED_MAC, link_up=False),
        _make_port("ens10f0", _USED_MAC, link_up=True),
    )
    assert list(discovery_redfish_networkadapters(section)) == [
        Service(item="1", parameters={"discovered_ports": [_USED_MAC]})
    ]


def test_warning_caused_only_by_unused_ports_is_ok() -> None:
    section = _make_adapter(
        _make_port("ens10f1", _UNUSED_MAC, link_up=False),
        _make_port("ens10f0", _USED_MAC, link_up=True),
    )
    assert _worst_state({"discovered_ports": [_USED_MAC]}, section) == State.OK


def test_discovered_port_going_down_is_crit() -> None:
    section = _make_adapter(_make_port("ens10f0", _USED_MAC, link_up=False))
    results = list(check_redfish_networkadapters("1", {"discovered_ports": [_USED_MAC]}, section))
    assert (
        Result(state=State.CRIT, summary="Port ens10f0: LinkDown (was LinkUp at discovery)")
        in results
    )


def test_undiscovered_port_coming_up_is_warn() -> None:
    section = _make_adapter(_make_port("ens10f1", _UNUSED_MAC, link_up=True), health="OK")
    results = list(check_redfish_networkadapters("1", {"discovered_ports": []}, section))
    assert (
        Result(
            state=State.WARN,
            summary="Port ens10f1: LinkUp but not monitored, rediscover the service",
        )
        in results
    )


def test_critical_adapter_health_is_not_explained_by_warning_ports() -> None:
    section = _make_adapter(_make_port("ens10f1", _UNUSED_MAC, link_up=False), health="Critical")
    assert _worst_state({"discovered_ports": []}, section) == State.CRIT


def test_identity_line_is_ok_on_unhealthy_adapter() -> None:
    section = _make_adapter(with_ports=False)
    results = list(check_redfish_networkadapters("1", {}, section))
    assert results[0] == Result(
        state=State.OK,
        summary=(
            "Model: Marvell 2P 10GbE 10GBASE-T QL41132HQRJ-HC OCP3 Adapter, "
            "SeNr: REE2227P38647, PartNr: AH2010415-30  C"
        ),
    )
    assert _worst_state({}, section) == State.WARN


def test_service_without_discovered_ports_keeps_adapter_health() -> None:
    section = _make_adapter(_make_port("ens10f1", _UNUSED_MAC, link_up=False))
    assert _worst_state({}, section) == State.WARN


def test_ports_without_mac_are_told_apart_by_name() -> None:
    section = _make_adapter(
        _make_port("ens10f1", None, link_up=False),
        _make_port("ens10f0", None, link_up=True),
    )
    assert list(discovery_redfish_networkadapters(section)) == [
        Service(item="1", parameters={"discovered_ports": ["ens10f0"]})
    ]
    assert _worst_state({"discovered_ports": ["ens10f0"]}, section) == State.OK


def test_discovery_skips_ports_without_any_identity() -> None:
    section = _make_adapter(
        _make_port(None, None, link_up=False),
        _make_port(None, None, link_up=True),
    )
    assert list(discovery_redfish_networkadapters(section)) == [
        Service(item="1", parameters={"discovered_ports": []})
    ]


def test_linkup_port_without_any_identity_is_warn() -> None:
    section = _make_adapter(
        _make_port(None, None, link_up=False),
        _make_port(None, None, link_up=True),
    )
    results = list(check_redfish_networkadapters("1", {"discovered_ports": []}, section))
    assert (
        Result(state=State.WARN, summary="Port without MAC or name: LinkUp but cannot be monitored")
        in results
    )


def test_adapter_warning_is_kept_when_unmonitored_port_is_critical() -> None:
    section = _make_adapter(
        _make_port("ens10f1", _UNUSED_MAC, link_up=False, down_health="Critical")
    )
    assert _worst_state({"discovered_ports": []}, section) == State.WARN


def test_discovery_treats_null_ports_as_no_ports() -> None:
    section = _make_adapter(null_ports=True)
    assert list(discovery_redfish_networkadapters(section)) == [
        Service(item="1", parameters={"discovered_ports": []})
    ]


def test_check_treats_null_ports_as_no_ports() -> None:
    section = _make_adapter(null_ports=True)
    assert _worst_state({"discovered_ports": []}, section) == State.WARN


def test_unknown_adapter_health_is_not_explained_by_unknown_port_health() -> None:
    section = _make_adapter(
        _make_port("ens10f1", _UNUSED_MAC, link_up=False, down_health="Degraded"),
        health="Degraded",
    )
    assert _worst_state({"discovered_ports": []}, section) == State.UNKNOWN


def test_discovered_port_no_longer_reported_is_crit() -> None:
    section = _make_adapter(_make_port("ens10f1", _UNUSED_MAC, link_up=False))
    results = list(check_redfish_networkadapters("1", {"discovered_ports": [_USED_MAC]}, section))
    assert (
        Result(
            state=State.CRIT, summary=f"Port {_USED_MAC}: not reported (was LinkUp at discovery)"
        )
        in results
    )
