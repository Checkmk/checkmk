#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks
from typing import Any, Mapping, Sequence


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param(
            (
                "freeipmi",
                {
                    "username": "user",
                    "password": "password",
                    "privilege_lvl": "user",
                },
            ),
            [
                "address",
                "user",
                "password",
                "user",
                "freeipmi",
            ],
            id="freeipmi with mandatory args only",
        ),
        pytest.param(
            (
                "freeipmi",
                {
                    "username": "user",
                    "ipmi_driver": "driver",
                    "password": "password",
                    "privilege_lvl": "user",
                    "sdr_cache_recreate": True,
                    "interpret_oem_data": True,
                    "output_sensor_state": False,
                },
            ),
            [
                "address",
                "user",
                "password",
                "user",
                "freeipmi",
                "--driver",
                "driver",
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
                    "password": "password",
                    "privilege_lvl": "user",
                    "intf": "lanplus",
                },
            ),
            [
                "address",
                "user",
                "password",
                "user",
                "ipmitool",
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
