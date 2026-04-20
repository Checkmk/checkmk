#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class _Params(BaseModel, frozen=True):
    regions: Sequence[str]


def _commands_function(
    params: _Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    yield SpecialAgentCommand(
        command_arguments=[region.replace("_", "-") for region in params.regions]
    )


special_agent_gcp_status = SpecialAgentConfig(
    name="gcp_status",
    parameter_parser=_Params.model_validate,
    commands_function=_commands_function,
)
