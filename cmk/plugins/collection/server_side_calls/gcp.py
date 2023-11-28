#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from collections.abc import Iterator, Mapping
from typing import Literal

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    get_secret_from_params,
    HostConfig,
    HTTPProxy,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class PiggyBackServices(BaseModel):
    piggyback_services: list[str] = Field(default_factory=list)
    prefix: str | None = None


class GCPCost(BaseModel):
    tableid: str


class Params(BaseModel):
    project: str
    credentials: tuple[Literal["password", "store"], str]
    cost: GCPCost | None = None
    piggyback: PiggyBackServices = Field(default_factory=PiggyBackServices)
    services: list[str] = Field(default_factory=list)


def agent_gcp_arguments(
    params: Params,
    _host_config: HostConfig,
    _http_proxies: Mapping[str, HTTPProxy],
) -> Iterator[SpecialAgentCommand]:
    today = datetime.date.today()
    args = [
        "--project",
        params.project,
        "--credentials",
        get_secret_from_params(params.credentials[0], params.credentials[1]),
        "--date",
        today.isoformat(),
    ]
    if params.cost is not None:
        args.append("--cost_table")
        args.append(params.cost.tableid)
    if len(params.services) > 0 or len(params.piggyback.piggyback_services) > 0:
        args.append("--services")
    if len(params.services) > 0:
        args.extend(params.services)
    if len(params.piggyback.piggyback_services):
        args.extend(params.piggyback.piggyback_services)

    args.append("--piggy-back-prefix")
    if params.piggyback.prefix is not None:
        args.append(params.piggyback.prefix)
    else:
        args.append(params.project)

    yield SpecialAgentCommand(command_arguments=args)


special_agent_gcp = SpecialAgentConfig(
    name="gcp",
    parameter_parser=Params.model_validate,
    commands_function=agent_gcp_arguments,
)
