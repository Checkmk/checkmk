#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping

from cmk.server_side_calls.v1 import (
    HostConfig,
    noop_parser,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def commands_function_alertmanager(
    params: Mapping[str, object], host_config: HostConfig, _http_proxies: object
) -> Iterator[SpecialAgentCommand]:
    alertmanager_params = {
        **params,
        "host_address": host_config.primary_ip_config.address,
        "host_name": host_config.name,
    }
    yield SpecialAgentCommand(command_arguments=[], stdin=repr(alertmanager_params))


special_agent_alertmanager = SpecialAgentConfig(
    name="alertmanager",
    parameter_parser=noop_parser,
    commands_function=commands_function_alertmanager,
)
