#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_volumes import (
    check_redfish_volumes,
    discovery_redfish_volumes,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple, RedfishAPIData

_HEALTHY = {"Health": "OK", "State": "Enabled"}


def _volume(**fields: object) -> dict[str, object]:
    return {
        "@odata.id": "/redfish/v1/Systems/0/Storage/1/Volumes/4",
        "@odata.type": "#Volume.v1_6_2.Volume",
        "Id": "4",
        "RAIDType": "RAID1",
        "CapacityBytes": 600127266816,
        "Status": _HEALTHY,
        **fields,
    }


def _volumes_section(*entries: Mapping[str, object]) -> RedfishAPIData:
    string_table: StringTable = [[json.dumps(entry)] for entry in entries]
    return parse_redfish_multiple(string_table)


def test_volumes_are_discovered_by_id_with_classic_naming() -> None:
    section = _volumes_section(_volume())

    assert list(discovery_redfish_volumes({"item": "classic"}, section)) == [Service(item="4")]


def test_volumes_are_discovered_by_system_controller_and_volume_on_request() -> None:
    section = _volumes_section(_volume())

    assert list(discovery_redfish_volumes({"item": "ctrlid"}, section)) == [Service(item="0:1:4")]


@pytest.mark.parametrize(
    "item",
    [
        pytest.param("4", id="classic item"),
        pytest.param("0:1:4", id="ctrlid item"),
    ],
)
def test_volume_raid_type_and_size_are_reported(item: str) -> None:
    section = _volumes_section(_volume())

    assert list(check_redfish_volumes(item, section))[0] == Result(
        state=State.OK, summary="Raid Type: RAID1, Size: 558.9GB"
    )


def test_critical_volume_health_makes_the_service_crit() -> None:
    section = _volumes_section(_volume(Status={"Health": "Critical", "State": "Enabled"}))

    assert list(check_redfish_volumes("4", section))[-1] == Result(
        state=State.CRIT,
        notice="Component State: A critical condition requires immediate attention., "
        "This resource is enabled.",
    )


def test_vanished_volume_yields_no_result() -> None:
    section = _volumes_section(_volume())

    assert list(check_redfish_volumes("5", section)) == []
