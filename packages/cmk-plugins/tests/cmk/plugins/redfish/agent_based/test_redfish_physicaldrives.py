#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.redfish.agent_based.redfish_physicaldrives import (
    check_redfish_physicaldrives,
    discovery_redfish_physicaldrives,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple, RedfishAPIData

_HPE_DISK_DRIVE: dict[str, object] = {
    "@odata.id": "/redfish/v1/Systems/1/SmartStorage/ArrayControllers/0/DiskDrives/0",
    "@odata.type": "#HpeSmartStorageDiskDrive.v2_1_0.HpeSmartStorageDiskDrive",
    "Id": "0",
    "Name": "HpeSmartStorageDiskDrive",
    "Location": "1I:1:1",
    "CapacityMiB": 572325,
    "InterfaceSpeedMbps": 12000,
    "MediaType": "HDD",
    "Model": "EG0600FBVFP",
    "SerialNumber": "KWK1DKDF",
    "Status": {"Health": "OK", "State": "Enabled"},
}

_OK_HEALTH = Result(state=State.OK, notice="Component State: Normal, This resource is enabled.")
_SERIAL_AND_MODEL = Result(state=State.OK, notice="Serial: KWK1DKDF\nModel: EG0600FBVFP")


def _section(*drives: dict[str, object]) -> RedfishAPIData:
    return parse_redfish_multiple([[json.dumps(drive)] for drive in drives])


def test_discovery_redfish_physicaldrives_names_items_by_controller_and_location() -> None:
    section = _section(
        _HPE_DISK_DRIVE,
        _HPE_DISK_DRIVE
        | {
            "@odata.id": "/redfish/v1/Systems/1/SmartStorage/ArrayControllers/2/DiskDrives/1",
            "Id": "1",
            "Location": "2I:1:5",
        },
    )

    assert list(discovery_redfish_physicaldrives(section)) == [
        Service(item="0:1I:1:1"),
        Service(item="2:2I:1:5"),
    ]


def test_discovery_redfish_physicaldrives_falls_back_to_name_without_location() -> None:
    section = _section(_HPE_DISK_DRIVE | {"Location": []})

    assert list(discovery_redfish_physicaldrives(section)) == [
        Service(item="0:HpeSmartStorageDiskDrive")
    ]


def test_check_redfish_physicaldrives_hdd_in_mib_and_mbps() -> None:
    section = _section(_HPE_DISK_DRIVE | {"CurrentTemperatureCelsius": 31})

    assert list(check_redfish_physicaldrives("0:1I:1:1", section)) == [
        Result(state=State.OK, summary="Size: 559GB, Speed 12.0 Gbs"),
        _OK_HEALTH,
        _SERIAL_AND_MODEL,
        Metric("temp", 31),
    ]


def test_check_redfish_physicaldrives_prefers_bytes_and_gbs() -> None:
    section = _section(_HPE_DISK_DRIVE | {"CapacityBytes": 1200243695616, "CapableSpeedGbs": 6})

    assert list(check_redfish_physicaldrives("0:1I:1:1", section)) == [
        Result(state=State.OK, summary="Size: 1118GB, Speed 6 Gbs"),
        _OK_HEALTH,
        _SERIAL_AND_MODEL,
    ]


@pytest.mark.parametrize(
    ["ssd_fields", "expected_metric", "expected_life_left"],
    [
        pytest.param(
            {"PredictedMediaLifeLeftPercent": 97},
            Metric("media_life_left", 97),
            97,
            id="predicted_life_left",
        ),
        pytest.param(
            {"SSDEnduranceUtilizationPercentage": 3},
            Metric("ssd_utilization", 3),
            97,
            id="endurance_utilization",
        ),
    ],
)
def test_check_redfish_physicaldrives_ssd_media_life(
    ssd_fields: dict[str, int], expected_metric: Metric, expected_life_left: int
) -> None:
    section = _section(_HPE_DISK_DRIVE | {"MediaType": "SSD"} | ssd_fields)

    assert list(check_redfish_physicaldrives("0:1I:1:1", section)) == [
        expected_metric,
        Result(
            state=State.OK,
            summary=f"Size: 559GB, Speed 12.0 Gbs, Media Life Left: {expected_life_left}%",
        ),
        _OK_HEALTH,
        _SERIAL_AND_MODEL,
    ]


def test_check_redfish_physicaldrives_ssd_without_wear_data() -> None:
    section = _section(_HPE_DISK_DRIVE | {"MediaType": "SSD"})

    assert list(check_redfish_physicaldrives("0:1I:1:1", section)) == [
        Result(state=State.OK, summary="Size: 559GB, Speed 12.0 Gbs"),
        _OK_HEALTH,
        _SERIAL_AND_MODEL,
    ]


def test_check_redfish_physicaldrives_reports_health() -> None:
    section = _section(_HPE_DISK_DRIVE | {"Status": {"Health": "Critical", "State": "Enabled"}})

    assert list(check_redfish_physicaldrives("0:1I:1:1", section))[1] == Result(
        state=State.CRIT,
        notice="Component State: A critical condition requires immediate attention., "
        "This resource is enabled.",
    )


def test_check_redfish_physicaldrives_unknown_item() -> None:
    assert not list(check_redfish_physicaldrives("0:9I:9:9", _section(_HPE_DISK_DRIVE)))
