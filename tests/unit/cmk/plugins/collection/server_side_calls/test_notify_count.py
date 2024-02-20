#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.collection.server_side_calls.notify_count import active_check_notify_count
from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    HostConfig,
    IPAddressFamily,
    NetworkAddressConfig,
    ResolvedIPAddressFamily,
)

HOST_CONFIG = HostConfig(
    name="host",
    resolved_address="address",
    alias="alias",
    address_config=NetworkAddressConfig(
        ip_family=IPAddressFamily.IPV4,
    ),
    resolved_ip_family=ResolvedIPAddressFamily.IPV4,
)


@pytest.mark.parametrize(
    "params,expected_result",
    [
        (
            {"description": "foo", "interval": 60},
            [ActiveCheckCommand(service_description="Notify foo", command_arguments=["-r", "60"])],
        ),
        (
            {"description": "foo", "interval": 60, "num_per_contact": (20, 50)},
            [
                ActiveCheckCommand(
                    service_description="Notify foo",
                    command_arguments=["-r", "60", "-w", "20", "-c", "50"],
                )
            ],
        ),
    ],
)
def test_check_notify_count_argument_parsing(
    params: Mapping[str, object], expected_result: Sequence[ActiveCheckCommand]
) -> None:
    """Tests if all required arguments are present."""
    parsed_params = active_check_notify_count.parameter_parser(params)
    assert (
        list(active_check_notify_count.commands_function(parsed_params, HOST_CONFIG, {}))
        == expected_result
    )
