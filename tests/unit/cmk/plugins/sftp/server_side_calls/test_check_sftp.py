#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.sftp.server_side_calls.check_sftp import active_check_sftp
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, Secret

HOST_CONFIG = HostConfig(name="hostname")


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param(
            {
                "host": "foo",
                "user": "bar",
                "secret": Secret(0),
                "look_for_keys": True,
            },
            (
                "--host",
                "foo",
                "--user",
                "bar",
                "--secret-reference",
                Secret(0),
                "--look-for-keys",
            ),
            id="look for keys",
        ),
        pytest.param(
            {
                "host": "foo",
                "user": "bar",
                "secret": Secret(0),
                "look_for_keys": False,
            },
            (
                "--host",
                "foo",
                "--user",
                "bar",
                "--secret-reference",
                Secret(0),
            ),
            id="do not look for keys",
        ),
    ],
)
def test_check_sftp_argument_parsing(
    params: Mapping[str, object],
    expected_args: Sequence[str],
) -> None:
    """Tests if all required arguments are present."""
    assert list(active_check_sftp(params, HOST_CONFIG)) == [
        ActiveCheckCommand(
            service_description="SFTP foo",
            command_arguments=expected_args,
        )
    ]
