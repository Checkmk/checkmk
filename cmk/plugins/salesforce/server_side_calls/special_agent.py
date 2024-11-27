#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class _Params(BaseModel, frozen=True):
    instances: list[str]


def command_function(params: _Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    args = [
        item
        for instance in params.instances
        for item in [
            "--section_url",
            f"salesforce_instances,https://api.status.salesforce.com/v1/instances/{instance}/status",
        ]
    ]
    yield SpecialAgentCommand(command_arguments=args)


special_agent_salesforce = SpecialAgentConfig(
    name="salesforce",
    parameter_parser=_Params.model_validate,
    commands_function=command_function,
)
