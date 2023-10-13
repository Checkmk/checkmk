#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from tests.testlib import ActiveCheck

from tests.unit.conftest import FixRegister

from cmk.config_generation.v1 import ActiveService, HostConfig, IPAddressFamily

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
            ActiveService("Aggr foo", ["-b", "some/path", "-a", "foo", "--use-automation-user"]),
        ),
    ],
)
def test_check_bi_aggr_argument_parsing(
    params: Mapping[str, object],
    expected_service: ActiveService,
    fix_register: FixRegister,
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("bi_aggr")
    services = list(active_check.run_service_function(HOST_CONFIG, {}, params))
    assert len(services) == 1
    assert services[0] == expected_service
