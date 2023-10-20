#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Iterator

from pydantic import BaseModel

from cmk.config_generation.v1 import HostConfig, HTTPProxy, SpecialAgentCommand, SpecialAgentConfig


class AzureStatusParams(BaseModel):
    regions: Sequence[str]


def agent_azure_status_config(
    params: AzureStatusParams,
    _host_config: HostConfig,
    _http_proxies: Mapping[str, HTTPProxy],
) -> Iterator[SpecialAgentCommand]:
    yield SpecialAgentCommand(command_arguments=params.regions)


special_agent_azure_status = SpecialAgentConfig(
    name="azure_status",
    parameter_parser=AzureStatusParams.model_validate,
    commands_function=agent_azure_status_config,
)
