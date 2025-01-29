#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class _Params(BaseModel, frozen=True):
    user: str | None = None
    password: Secret | None = None
    infos: Sequence[str]


def _commands_function(
    params: _Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    auth_args: list[str | Secret] = []
    if params.user:
        auth_args += ["-u", params.user]
    if params.password:
        auth_args += ["-p", params.password.unsafe()]
    yield SpecialAgentCommand(
        command_arguments=[
            *auth_args,
            "-i",
            ",".join(params.infos),
            host_config.primary_ip_config.address,
        ]
    )


special_agent_emcvnx = SpecialAgentConfig(
    name="emcvnx",
    parameter_parser=_Params.model_validate,
    commands_function=_commands_function,
)
