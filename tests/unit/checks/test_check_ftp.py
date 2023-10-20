#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param({}, ["-H", "$HOSTADDRESS$"], id="params empty"),
        pytest.param({"port": 21}, ["-H", "$HOSTADDRESS$", "-p", 21], id="some params present"),
        pytest.param(
            {
                "port": 21,
                "response_time": (100.0, 200.0),
                "timeout": 10,
                "refuse_state": "crit",
                "send_string": "abc",
                "expect": ["cde"],
                "ssl": True,
                "cert_days": (5, 6),
            },
            [
                "-H",
                "$HOSTADDRESS$",
                "-p",
                21,
                "-w",
                "0.100000",
                "-c",
                "0.200000",
                "-t",
                10,
                "-r",
                "crit",
                "-s",
                "abc",
                "-e",
                "cde",
                "--ssl",
                "-D",
                5,
                6,
            ],
            id="all params present",
        ),
    ],
)
def test_check_ftp_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[object]
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_ftp")
    assert active_check.run_argument_function(params) == expected_args


@pytest.mark.parametrize(
    "params, expected_item",
    [
        pytest.param({}, "FTP", id="no port"),
        pytest.param({"port": 21}, "FTP", id="port 21"),
        pytest.param({"port": 22}, "FTP Port 22", id="port different from 21"),
    ],
)
def test_check_ftp_get_item(params: Mapping[str, object], expected_item: str) -> None:
    active_check = ActiveCheck("check_ftp")
    assert active_check.run_service_description(params) == expected_item
