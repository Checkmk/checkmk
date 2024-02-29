#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.collection.server_side_calls.check_sftp import active_check_sftp
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config, Secret

SOME_HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address=None),
)


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param(
            {"host": "foo", "user": "bar", "secret": Secret(0), "look_for_keys": True},
            (
                ActiveCheckCommand(
                    service_description="SFTP foo",
                    command_arguments=(
                        "--host=foo",
                        "--user=bar",
                        Secret(0, "--secret=%s"),
                        "--look-for-keys",
                    ),
                ),
            ),
            id="look for keys",
        ),
        pytest.param(
            {"host": "foo", "user": "bar", "secret": Secret(0)},
            (
                ActiveCheckCommand(
                    service_description="SFTP foo",
                    command_arguments=(
                        "--host=foo",
                        "--user=bar",
                        Secret(0, "--secret=%s"),
                    ),
                ),
            ),
            id="don't look for keys",
        ),
        pytest.param(
            {
                "host": "foo",
                "user": "bar",
                "secret": Secret(0),
                "get": {"remote": "my/remote/get", "local": "my/local/get"},
                "put": {"remote": "my/remote/put", "local": "my/local/put"},
            },
            (
                ActiveCheckCommand(
                    service_description="SFTP foo",
                    command_arguments=(
                        "--host=foo",
                        "--user=bar",
                        Secret(0, "--secret=%s"),
                        "--put-local=my/local/put",
                        "--put-remote=my/remote/put",
                        "--get-local=my/local/get",
                        "--get-remote=my/remote/get",
                    ),
                ),
            ),
            id="get & put",
        ),
    ],
)
def test_check_sftp_argument_parsing(
    params: Mapping[str, object],
    expected_args: tuple[ActiveCheckCommand],
) -> None:
    """Tests if all required arguments are present."""
    assert tuple(active_check_sftp(params, SOME_HOST_CONFIG, {})) == expected_args
