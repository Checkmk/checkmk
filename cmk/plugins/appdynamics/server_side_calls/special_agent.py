#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class _Params(BaseModel, frozen=True):
    username: str
    password: Secret
    application: str
    port: int | None = None
    timeout: int | None = None


def _commands_function(
    params: _Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "-u",
        params.username,
        "-p",
        params.password.unsafe(),
    ]

    if params.port is not None:
        args += ["-P", str(params.port)]

    if params.timeout is not None:
        args += ["-t", str(params.timeout)]

    args += [
        host_config.primary_ip_config.address,
        params.application,
    ]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_appdynamics = SpecialAgentConfig(
    name="appdynamics",
    parameter_parser=_Params.model_validate,
    commands_function=_commands_function,
)
