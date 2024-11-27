#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class Params(BaseModel):
    random: None


def command_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    yield SpecialAgentCommand(command_arguments=[host_config.name])


special_agent_random = SpecialAgentConfig(
    name="random",
    parameter_parser=Params.model_validate,
    commands_function=command_function,
)
