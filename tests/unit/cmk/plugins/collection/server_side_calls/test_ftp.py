#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.collection.server_side_calls.ftp import active_check_ftp
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="0.0.0.1"),
)


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param(
            {},
            [ActiveCheckCommand(service_description="FTP", command_arguments=["-H", "0.0.0.1"])],
            id="params empty",
        ),
        pytest.param(
            {"port": 21},
            [
                ActiveCheckCommand(
                    service_description="FTP", command_arguments=["-H", "0.0.0.1", "-p", "21"]
                )
            ],
            id="some params present",
        ),
        pytest.param(
            {
                "port": 22,
                "response_time": (100.0, 200.0),
                "timeout": 10,
                "refuse_state": "crit",
                "send_string": "abc",
                "expect": ["cde"],
                "ssl": True,
                "cert_days": (5, 6),
            },
            [
                ActiveCheckCommand(
                    service_description="FTP Port 22",
                    command_arguments=[
                        "-H",
                        "0.0.0.1",
                        "-p",
                        "22",
                        "-w",
                        "0.100000",
                        "-c",
                        "0.200000",
                        "-t",
                        "10",
                        "-r",
                        "crit",
                        "-s",
                        "abc",
                        "-e",
                        "cde",
                        "--ssl",
                        "-D",
                        "5",
                        "6",
                    ],
                )
            ],
            id="all params present",
        ),
    ],
)
def test_check_ftp_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[ActiveCheckCommand]
) -> None:
    """Tests if all required arguments are present."""
    assert list(active_check_ftp(params, HOST_CONFIG)) == expected_args
