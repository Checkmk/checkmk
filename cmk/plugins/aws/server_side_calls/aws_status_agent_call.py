#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class AwsStatusParams(BaseModel):
    regions_to_monitor: Sequence[str]


def aws_status_arguments(
    params: AwsStatusParams,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    args = [region.replace("_", "-") for region in params.regions_to_monitor]
    yield SpecialAgentCommand(command_arguments=args)


special_agent_aws_status = SpecialAgentConfig(
    name="aws_status",
    parameter_parser=AwsStatusParams.model_validate,
    commands_function=aws_status_arguments,
)
