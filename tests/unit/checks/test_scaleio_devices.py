#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

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
def fixture_scaleio_devices(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("scaleio_devices")]


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
                    notice=(
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
