#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.config_generation.v1 import ActiveCheckCommand, HostConfig, IPAddressFamily
from cmk.plugins.collection.config_generation.bi_aggr import active_check_bi_aggr

HOST_CONFIG = HostConfig(
    name="hostname",
    address="0.0.0.1",
    alias="host_alias",
    ip_family=IPAddressFamily.IPv4,
    ipv4address=None,
    ipv6address=None,
    additional_ipv4addresses=[],
    additional_ipv6addresses=[],
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
        active_check_bi_aggr.service_function(
            active_check_bi_aggr.parameter_parser(params), HOST_CONFIG, {}
        )
    )
    assert services == [expected_service]
