#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            (
                "freeipmi",
                {
                    "username": "user",
                    "password": ("password", "password"),
                    "privilege_lvl": "user",
                    "cipher_suite_id": "suite_3",
                },
            ),
            [
                "address",
                "user",
                "password",
                "freeipmi",
                "user",
                "--cipher_suite_id",
                "3",
                "--output_sensor_state",
            ],
            id="freeipmi with mandatory args only and explicit password",
        ),
        pytest.param(
            (
                "freeipmi",
                {
                    "username": "user",
                    "password": ("store", "ipmi_sensors"),
                    "privilege_lvl": "user",
                    "cipher_suite_id": "suite_3",
                },
            ),
            [
                "address",
                "user",
                ("store", "ipmi_sensors", "%s"),
                "freeipmi",
                "user",
                "--cipher_suite_id",
                "3",
                "--output_sensor_state",
            ],
            id="freeipmi with mandatory args only and password from the store",
        ),
        pytest.param(
            (
                "freeipmi",
                {
                    "username": "user",
                    "ipmi_driver": "driver",
                    "password": ("password", "password"),
                    "privilege_lvl": "user",
                    "sdr_cache_recreate": True,
                    "interpret_oem_data": True,
                    "output_sensor_state": False,
                    "cipher_suite_id": "suite_17",
                },
            ),
            [
                "address",
                "user",
                "password",
                "freeipmi",
                "user",
                "--driver",
                "driver",
                "--cipher_suite_id",
                "17",
                "--sdr_cache_recreate",
                "--interpret_oem_data",
            ],
            id="freeipmi with optional args",
        ),
        pytest.param(
            (
                "ipmitool",
                {
                    "username": "user",
                    "password": ("password", "password"),
                    "privilege_lvl": "administrator",
                    "intf": "lanplus",
                },
            ),
            [
                "address",
                "user",
                "password",
                "ipmitool",
                "administrator",
                "--intf",
                "lanplus",
            ],
            id="ipmitool with optional arg",
        ),
    ],
)
def test_ipmi_sensors_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[str],
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_ipmi_sensors")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
