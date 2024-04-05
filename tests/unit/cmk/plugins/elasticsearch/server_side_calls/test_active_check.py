#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest
from polyfactory.factories import DataclassFactory

from cmk.plugins.elasticsearch.server_side_calls.active_check import active_check_config as config
from cmk.server_side_calls.v1 import (
    HostConfig,
    IPAddressFamily,
    NetworkAddressConfig,
    ResolvedIPAddressFamily,
)


class HostConfigFactory(DataclassFactory):
    __model__ = HostConfig


@pytest.mark.parametrize(
    "params,host_config,expected_args,expected_description",
    [
        (
            {
                "svc_item": "stuff",
                "index": ["f", "o", "o"],
                "pattern": "bar",
                "timerange": 1,
            },
            HostConfigFactory.build(
                resolved_ipv4_address="test",
                resolved_ip_family=ResolvedIPAddressFamily.IPV4,
                address_config=NetworkAddressConfig(ip_family=IPAddressFamily.IPV4),
            ),
            ["-q", "bar", "-t", "1", "-i", "f o o", "-H", "test"],
            "Elasticsearch Query stuff",
        )
    ],
)
def test_check_elasticsearch_query(
    params: Mapping[str, object],
    host_config: HostConfig,
    expected_args: Sequence[str],
    expected_description: str,
) -> None:
    # Act
    parsed_params = config.parameter_parser(params)
    commands = list(config.commands_function(parsed_params, host_config, {}))
    # Assert
    assert len(commands) == 1
    assert commands[0].service_description == expected_description
    assert commands[0].command_arguments == expected_args
