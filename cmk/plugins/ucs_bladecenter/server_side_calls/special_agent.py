#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret


class _Params(BaseModel, frozen=True):
    username: str
    password: Secret
    certificate_validation: bool


def agent_ucsbladecenter_arguments(
    params: _Params, host_config: HostConfig
) -> Iterable[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = [
        "-u",
        params.username,
        "-p",
        params.password.unsafe(),
    ]

    if params.certificate_validation is False:
        command_arguments.append("--no-cert-check")
    else:
        command_arguments.extend(["--cert-server-name", host_config.name])

    command_arguments.append(host_config.primary_ip_config.address)

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_ucs_bladecenter = SpecialAgentConfig(
    name="ucs_bladecenter",
    parameter_parser=_Params.model_validate,
    commands_function=agent_ucsbladecenter_arguments,
)
