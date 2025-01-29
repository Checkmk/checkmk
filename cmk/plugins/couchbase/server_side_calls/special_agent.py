#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class _AuthenticationParams(BaseModel, frozen=True):
    username: str
    password: Secret


class _Params(BaseModel, frozen=True):
    buckets: Sequence[str] = []
    timeout: int | None = None
    port: int | None = None
    authentication: _AuthenticationParams | None = None


def _commands_function(
    params: _Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    args: list[str | Secret] = []

    for bucket in params.buckets:
        args = [*args, "--buckets", bucket]
    if params.timeout is not None:
        args = [*args, "--timeout", str(params.timeout)]
    if params.port is not None:
        args = [*args, "--port", str(params.port)]
    if params.authentication:
        args = [
            *args,
            "--username",
            params.authentication.username,
            "--password",
            params.authentication.password.unsafe(),
        ]

    yield SpecialAgentCommand(
        command_arguments=[
            *args,
            host_config.primary_ip_config.address,
        ]
    )


special_agent_couchbase = SpecialAgentConfig(
    name="couchbase",
    parameter_parser=_Params.model_validate,
    commands_function=_commands_function,
)
