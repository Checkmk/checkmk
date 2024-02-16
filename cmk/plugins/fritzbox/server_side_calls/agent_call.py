#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from cmk.plugins.fritzbox.lib.config import AgentConfigParams
from cmk.server_side_calls.v1 import HostConfig, HTTPProxy, SpecialAgentCommand, SpecialAgentConfig


def fritzbox_arguments(
    params: AgentConfigParams, host_config: HostConfig, proxies: Mapping[str, HTTPProxy]
) -> Iterable[SpecialAgentCommand]:
    if (
        host_config.resolved_address is None
    ):  # TODO: should it really be optional? we always have a host name.
        raise TypeError(host_config.resolved_address)

    yield SpecialAgentCommand(
        command_arguments=(
            *(() if params.timeout is None else ("--timeout", str(params.timeout))),
            host_config.resolved_address,
        )
    )


special_agent_fritzbox = SpecialAgentConfig(
    name="fritzbox",
    parameter_parser=AgentConfigParams.model_validate,
    commands_function=fritzbox_arguments,
)
