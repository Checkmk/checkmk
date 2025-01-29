#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class _Params(BaseModel, frozen=True):
    port: int | None = None
    segment_display_uid: str | None = None
    segment_display_brightness: int | None = None


def _commands_function(
    params: _Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    args = ["--host", host_config.primary_ip_config.address]
    if params.port is not None:
        args = [*args, "--port", str(params.port)]
    if params.segment_display_uid is not None:
        args = [*args, "--segment_display_uid", params.segment_display_uid]
    if params.segment_display_brightness is not None:
        args = [*args, "--segment_display_brightness", str(params.segment_display_brightness)]
    yield SpecialAgentCommand(command_arguments=args)


special_agent_tinkerforge = SpecialAgentConfig(
    name="tinkerforge",
    parameter_parser=_Params.model_validate,
    commands_function=_commands_function,
)
