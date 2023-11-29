#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.pure_storage_fa.server_side_calls.special_agent import commands_function, Params
from cmk.server_side_calls.v1 import (
    HostConfig,
    IPAddressFamily,
    PlainTextSecret,
    Secret,
    SpecialAgentCommand,
    StoredSecret,
)


@pytest.mark.parametrize(
    "params, host_ip_address, hostname, expected_arguments",
    [
        pytest.param(
            {
                "timeout": 1,
                "ssl": True,
                "api_token": ("store", "stored_secret"),
            },
            "1.2.3.4",
            "host",
            [
                "--timeout",
                "1",
                "--cert-server-name",
                "host",
                "--api-token",
                StoredSecret("stored_secret", format="%s"),
                "1.2.3.4",
            ],
            id="Available timeout and ssl True and stored api token and hostip available",
        ),
        pytest.param(
            {
                "ssl": False,
                "api_token": ("password", "api_token"),
            },
            "",
            "host",
            [
                "--no-cert-check",
                "--api-token",
                PlainTextSecret(value="api_token", format="%s"),
                "host",
            ],
            id="No timeout and ssl False and no hostip",
        ),
        pytest.param(
            {
                "ssl": "something_else",
                "api_token": ("password", "api_token"),
            },
            "1.2.3.4",
            "host",
            [
                "--cert-server-name",
                "something_else",
                "--api-token",
                PlainTextSecret(value="api_token", format="%s"),
                "1.2.3.4",
            ],
            id="No timeout and ssl custom and hostip available",
        ),
    ],
)
def test_commands_function(
    params: Mapping[str, object],
    host_ip_address: str,
    hostname: str,
    expected_arguments: Sequence[str | Secret],
) -> None:
    assert list(
        commands_function(
            Params.model_validate(params),
            HostConfig(
                name=hostname,
                address=host_ip_address,
                alias="host",
                ip_family=IPAddressFamily.IPV4,
            ),
            {},
        )
    ) == [SpecialAgentCommand(command_arguments=expected_arguments)]
