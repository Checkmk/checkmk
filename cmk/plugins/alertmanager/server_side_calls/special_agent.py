#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class AuthLogin(BaseModel, frozen=True):
    username: str
    password: Secret


class AuthToken(BaseModel, frozen=True):
    token: Secret


class IgnoreAlerts(BaseModel, frozen=True):
    ignore_na: bool
    ignore_alert_rules: Sequence[str]
    ignore_alert_groups: Sequence[str]


class Params(BaseModel, frozen=True):
    hostname: str
    connection: str
    verify_cert: bool
    auth_basic: (
        tuple[Literal["auth_login"], AuthLogin] | tuple[Literal["auth_token"], AuthToken] | None
    ) = None
    protocol: Literal["http", "https"]
    ignore_alerts: IgnoreAlerts


def _commands_function(
    params: Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "--config",
        repr(
            params.model_dump(
                exclude={
                    "auth_basic",
                    "verify_cert",
                },
            )
        ),
    ]
    if not params.verify_cert:
        args.append("--disable-cert-verification")
    # the authentication parameters must come last because they are parsed by subparsers that
    # consume all remaining arguments (and throw errors if they don't recognize them)
    match params.auth_basic:
        case ("auth_login", AuthLogin(username=username, password=password)):
            args += [
                "auth_login",
                "--username",
                username,
                "--password-reference",
                password,
            ]
        case ("auth_token", AuthToken(token=token)):
            args += [
                "auth_token",
                "--token",
                token,
            ]
    yield SpecialAgentCommand(command_arguments=args)


special_agent_alertmanager = SpecialAgentConfig(
    name="alertmanager",
    parameter_parser=Params.model_validate,
    commands_function=_commands_function,
)
