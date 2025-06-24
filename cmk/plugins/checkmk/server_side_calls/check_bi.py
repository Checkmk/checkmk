#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    replace_macros,
    Secret,
)


class Credentials(BaseModel, frozen=True):
    user: str
    secret: Secret


class OptionalParams(BaseModel, frozen=True):
    auth_mode: str | None = None
    timeout: float | None = None
    in_downtime: Literal["normal", "ok", "warn"] | None = None
    acknowledged: Literal["normal", "ok", "warn"] | None = None
    track_downtimes: bool = False


class BiAggrParams(BaseModel, frozen=True):
    base_url: str
    aggregation_name: str
    credentials: tuple[Literal["automation"], None] | tuple[Literal["credentials"], Credentials]
    optional: OptionalParams


def _check_bi_aggr_services(
    params: BiAggrParams, host_config: HostConfig
) -> Iterator[ActiveCheckCommand]:
    aggregation_name = replace_macros(params.aggregation_name, host_config.macros)
    base_url = replace_macros(params.base_url, host_config.macros)

    args: list[str | Secret] = ["-b", base_url, "-a", aggregation_name]
    match params.credentials[1]:
        case None:
            args.append("--use-automation-user")
        case Credentials() as cred:
            args += ["-u", cred.user, "--secret-reference", cred.secret]

    if params.optional.auth_mode:
        args += ["-m", params.optional.auth_mode]
    if params.optional.timeout is not None:
        args += ["-t", f"{params.optional.timeout:.0f}"]
    if params.optional.in_downtime:
        args += ["--in-downtime", params.optional.in_downtime]
    if params.optional.acknowledged:
        args += ["--acknowledged", params.optional.acknowledged]
    if params.optional.track_downtimes:
        args += ["-r", "-n", host_config.name]

    yield ActiveCheckCommand(service_description=aggregation_name, command_arguments=args)


active_check_bi_aggr = ActiveCheckConfig(
    name="bi_aggr",
    parameter_parser=BiAggrParams.model_validate,
    commands_function=_check_bi_aggr_services,
)
