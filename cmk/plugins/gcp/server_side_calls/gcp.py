#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from collections.abc import Iterator

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    HostConfig,
    replace_macros,
    Secret,
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
    credentials: Secret
    cost: GCPCost | None = None
    piggyback: PiggyBackServices = Field(default_factory=PiggyBackServices)
    services: list[str] = Field(default_factory=list)
    connection_test: bool = False  # only used by quick setup


def agent_gcp_arguments(
    params: Params,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    today = datetime.date.today()
    args: list[str | Secret] = [
        "--project",
        params.project,
        "--credentials",
        params.credentials.unsafe(),
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
        prefix = replace_macros(params.piggyback.prefix, host_config.macros)
        args.append(prefix)
    else:
        args.append(params.project)

    if params.connection_test:
        args.append("--connection-test")

    yield SpecialAgentCommand(command_arguments=args)


special_agent_gcp = SpecialAgentConfig(
    name="gcp",
    parameter_parser=Params.model_validate,
    commands_function=agent_gcp_arguments,
)
