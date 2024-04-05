#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.collection.server_side_calls.bi_aggr import active_check_bi_aggr
from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    HostConfig,
    IPAddressFamily,
    NetworkAddressConfig,
    ResolvedIPAddressFamily,
)

HOST_CONFIG = HostConfig(
    name="hostname",
    resolved_address="0.0.0.1",
    alias="host_alias",
    address_config=NetworkAddressConfig(
        ip_family=IPAddressFamily.IPV4,
        ipv4_address="0.0.0.1",
    ),
    resolved_ip_family=ResolvedIPAddressFamily.IPV4,
)


@pytest.mark.parametrize(
    "params,expected_service",
    [
        (
            {
                "base_url": "some/path",
                "aggregation_name": "foo",
                "username": "bar",
                "credentials": "automation",
                "optional": {},
            },
            ActiveCheckCommand(
                "Aggr foo", ["-b", "some/path", "-a", "foo", "--use-automation-user"]
            ),
        ),
    ],
)
def test_check_bi_aggr_argument_parsing(
    params: Mapping[str, object],
    expected_service: ActiveCheckCommand,
) -> None:
    """Tests if all required arguments are present."""
    services = list(
        active_check_bi_aggr.commands_function(
            active_check_bi_aggr.parameter_parser(params), HOST_CONFIG, {}
        )
    )
    assert services == [expected_service]
