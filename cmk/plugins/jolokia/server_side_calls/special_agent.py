#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret


class Login(BaseModel):
    user: str
    password: Secret
    mode: Literal["basic", "digest"]


class Params(BaseModel):
    port: int | None = None
    suburi: str | None = None
    instance: str | None = None
    protocol: str | None = None
    login: Login | None = None


def _get_login_options(login: Login | None) -> tuple[()] | tuple[str, str, str, Secret, str, str]:
    return (
        ("--user", login.user, "--password", login.password.unsafe(), "--mode", login.mode)
        if login
        else ()
    )


def commands_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    yield SpecialAgentCommand(
        command_arguments=[
            "--server",
            host_config.primary_ip_config.address,
            *(["--%s" % "port", "%s" % params.port] if params.port else []),
            *(["--%s" % "suburi", "%s" % params.suburi] if params.suburi else []),
            *(["--%s" % "instance", "%s" % params.instance] if params.instance else []),
            *(["--%s" % "protocol", "%s" % params.protocol] if params.protocol else []),
            *_get_login_options(params.login),
        ]
    )


special_agent_jolokia = SpecialAgentConfig(
    name="jolokia",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
