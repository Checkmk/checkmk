#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# 2019-01-17, comNET GmbH, Fabian Binder

from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class Params(BaseModel):
    authentication: str = "windows"
    username: str
    password: Secret


def commands_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    yield SpecialAgentCommand(
        command_arguments=[
            "--authentication",
            params.authentication,
            "-u",
            params.username,
            "-p",
            params.password.unsafe(),
            host_config.primary_ip_config.address,
        ]
    )


special_agent_zerto = SpecialAgentConfig(
    name="zerto",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
