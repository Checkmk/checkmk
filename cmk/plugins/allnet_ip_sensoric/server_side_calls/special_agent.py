#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class Params(BaseModel, frozen=True):
    timeout: float | None = None


def commands_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    yield SpecialAgentCommand(
        command_arguments=[
            *(["--timeout", f"{params.timeout:.0f}"] if params.timeout is not None else []),
            host_config.primary_ip_config.address,
        ]
    )


special_agent_allnet_ip_sensoric = SpecialAgentConfig(
    name="allnet_ip_sensoric",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
