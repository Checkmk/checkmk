#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.checkmk.server_side_calls.check_bi import active_check_bi_aggr
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config, Secret

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="0.0.0.1"),
    macros={
        "$HOST_NAME$": "hostname",
    },
)


@pytest.mark.parametrize(
    "params,expected_service",
    [
        pytest.param(
            {
                "base_url": "some/path",
                "aggregation_name": "foo",
                "username": "bar",
                "credentials": ("automation", None),
                "optional": {},
            },
            ActiveCheckCommand(
                service_description="foo",
                command_arguments=["-b", "some/path", "-a", "foo", "--use-automation-user"],
            ),
            id="required params",
        ),
        pytest.param(
            {
                "base_url": "some/path",
                "aggregation_name": "$HOST_NAME$",
                "username": "bar",
                "credentials": ("credentials", {"user": "my_user", "secret": Secret(0)}),
                "optional": {},
            },
            ActiveCheckCommand(
                service_description="hostname",
                command_arguments=[
                    "-b",
                    "some/path",
                    "-a",
                    "hostname",
                    "-u",
                    "my_user",
                    "--secret-reference",
                    Secret(0),
                ],
            ),
            id="aggregation name with macro",
        ),
    ],
)
def test_check_bi_aggr_argument_parsing(
    params: Mapping[str, object],
    expected_service: ActiveCheckCommand,
) -> None:
    services = list(active_check_bi_aggr(params, HOST_CONFIG))
    assert services == [expected_service]
