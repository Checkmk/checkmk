#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="list-item"

from collections.abc import Iterable, Mapping

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret


class Params(BaseModel):
    port: int | None = None
    suburi: str | None = None
    instance: str | None = None
    protocol: str | None = None
    login: Mapping[str, str | Secret] | None = None


def commands_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    command_arguments = ["--server", host_config.primary_ip_config.address]

    command_arguments += ["--%s" % "port", "%s" % params.port] if params.port else []
    command_arguments += ["--%s" % "suburi", "%s" % params.suburi] if params.suburi else []
    command_arguments += ["--%s" % "instance", "%s" % params.instance] if params.instance else []
    command_arguments += ["--%s" % "protocol", "%s" % params.protocol] if params.protocol else []

    if not params.login:
        yield SpecialAgentCommand(command_arguments=command_arguments)
        return

    user = params.login["user"]
    password = params.login["password"]
    assert isinstance(password, Secret)
    mode = params.login["mode"]

    command_arguments += [
        "--user",
        user,
        f"--password {password.unsafe()}",
        "--mode",
        mode,
    ]

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_jolokia = SpecialAgentConfig(
    name="jolokia",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
