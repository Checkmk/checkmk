#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class _Params(BaseModel, frozen=True):
    user: str
    accept_any_hostkey: bool
    infos: Sequence[str]


def _commands_function(
    params: _Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    args = ["-u", params.user, "-i", ",".join(params.infos)]
    if params.accept_any_hostkey:
        args += ["--accept-any-hostkey"]
    args.append(host_config.primary_ip_config.address)
    yield SpecialAgentCommand(command_arguments=args)


special_agent_ibmsvc = SpecialAgentConfig(
    name="ibmsvc",
    parameter_parser=_Params.model_validate,
    commands_function=_commands_function,
)
