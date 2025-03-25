#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class _AuthBasic(BaseModel, frozen=True):
    username: str
    password: Secret


class _Params(BaseModel, frozen=True):
    protocol: str | None = None
    cert_verification: bool
    auth_basic: _AuthBasic


def _commands_function(
    params: _Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    args: list[str | Secret] = [
        host_config.name,
        params.auth_basic.username,
        params.auth_basic.password.unsafe(),
    ]
    if params.protocol:
        args.extend(["--protocol", params.protocol])
    if not params.cert_verification:
        args.append("--no-cert-check")
    yield SpecialAgentCommand(command_arguments=args)


special_agent_innovaphone = SpecialAgentConfig(
    name="innovaphone",
    parameter_parser=_Params.model_validate,
    commands_function=_commands_function,
)
