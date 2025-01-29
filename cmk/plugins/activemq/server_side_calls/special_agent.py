#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class BasicAuth(BaseModel, frozen=True):
    username: str
    password: Secret


class Params(BaseModel, frozen=True):
    servername: str
    port: int
    protocol: str
    use_piggyback: bool
    basicauth: BasicAuth | None = None


def _commands_function(
    params: Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    basic_auth_args: list[str | Secret] = (
        [
            "--username",
            params.basicauth.username,
            "--password",
            params.basicauth.password.unsafe(),
        ]
        if params.basicauth
        else []
    )

    yield SpecialAgentCommand(
        command_arguments=(
            [
                params.servername,
                str(params.port),
                "--protocol",
                params.protocol,
                *(["--piggyback"] if params.use_piggyback else []),
                *basic_auth_args,
            ]
        )
    )


special_agent_activemq = SpecialAgentConfig(
    name="activemq",
    parameter_parser=Params.model_validate,
    commands_function=_commands_function,
)
