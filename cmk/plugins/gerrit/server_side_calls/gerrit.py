#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    replace_macros,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class GerritParams(BaseModel):
    instance: str
    user: str
    password: Secret
    protocol: Literal["http", "https"] | None = None
    port: int | None = None
    version_cache: float | None = None


def agent_gerrit_config(
    params: GerritParams, host_config: HostConfig
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = ["--user", params.user, "--password-ref", params.password]

    if params.protocol:
        args.extend(["--proto", params.protocol])

    if params.port:
        args.extend(["--port", str(params.port)])

    if params.version_cache:
        args.extend(["--version-cache", str(params.version_cache)])

    args.append(replace_macros(params.instance, host_config.macros))

    yield SpecialAgentCommand(command_arguments=args)


special_agent_gerrit = SpecialAgentConfig(
    name="gerrit",
    parameter_parser=GerritParams.model_validate,
    commands_function=agent_gerrit_config,
)
