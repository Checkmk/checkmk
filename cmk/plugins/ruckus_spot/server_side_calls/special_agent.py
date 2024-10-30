#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import assert_never, Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret


class _CmkAgent(BaseModel, frozen=True):
    port: int


class Params(BaseModel, frozen=True):
    address: tuple[Literal["use_host_address"], None] | tuple[Literal["manual_address"], str]
    port: int
    venueid: str
    api_key: Secret
    cmk_agent: _CmkAgent | None = None


def command_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = []

    if params.address[0] == "use_host_address":
        command_arguments += [
            "--address",
            f"{host_config.primary_ip_config.address}:{params.port}",
        ]
    elif params.address[0] == "manual_address":
        command_arguments += ["--address", f"{params.address[1]}:{params.port}"]
    else:
        assert_never(params.address)

    command_arguments += ["--venueid", params.venueid]
    command_arguments += ["--apikey", params.api_key.unsafe()]

    if params.cmk_agent is not None:
        command_arguments += ["--agent_port", "%s" % params.cmk_agent.port]

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_ruckus_spot = SpecialAgentConfig(
    name="ruckus_spot",
    parameter_parser=Params.model_validate,
    commands_function=command_function,
)
