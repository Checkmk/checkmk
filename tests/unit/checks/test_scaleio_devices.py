#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.checkengine.plugins import AgentBasedPlugins, CheckPlugin, CheckPluginName

_SECTION = {
    "devices": [
        {
            "DEVICE": "afab08ad00000001",
            "ERR_STATE": "NO_ERROR",
            "ID": "afab08ad00000001",
            "SDS_ID": "cf8420ab00000000",
            "STATE": "DEVICE_NORMAL",
            "STORAGE_POOL_ID": "5981e28b00000001",
        },
        {
            "DEVICE": "afab08b100000002",
            "ERR_STATE": "ERROR",
            "ID": "afab08b100000002",
            "SDS_ID": "cf8420ab00000000",
            "STATE": "DEVICE_ERROR",
            "STORAGE_POOL_ID": "5981e28b00000001",
        },
        {
            "DEVICE": "afab08ec00000000",
            "ID": "afab08ec00000000",
            "SDS_ID": "cf8420ab00000000",
        },
    ]
}


@pytest.fixture(name="scaleio_devices")
def fixture_scaleio_devices(agent_based_plugins: AgentBasedPlugins) -> CheckPlugin:
    return agent_based_plugins.check_plugins[CheckPluginName("scaleio_devices")]


def test_discover_scaleio_devices(scaleio_devices: CheckPlugin) -> None:
    assert list(scaleio_devices.discovery_function(_SECTION)) == [
        Service(item="devices"),
    ]


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "devices",
            [
                Result(
                    state=State.CRIT,
                    summary="3 devices, 2 errors (afab08b100000002, afab08ec00000000)",
                ),
                Result(
                    state=State.OK,
                    summary="2 additional details available",
                    details=(
                        "Device afab08b100000002: Error: device error, State: error (ID: afab08b100000002, Storage pool ID: 5981e28b00000001)\n"
                        "Device afab08ec00000000: Error: n/a, State: n/a (ID: afab08ec00000000, Storage pool ID: n/a)"
                    ),
                ),
            ],
            id="scaleio_devices",
        ),
    ],
)
def test_check_scaleio_devices(
    scaleio_devices: CheckPlugin,
    item: str,
    expected_result: list[Result],
) -> None:
    assert (
        list(
            scaleio_devices.check_function(
                item=item,
                params={},
                section=_SECTION,
            )
        )
        == expected_result
    )
