#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Iterator

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    HTTPProxy,
    parse_secret,
    Secret,
)

from .utils import SecretType


class Credentials(BaseModel):
    automation: bool = False
    user: str | None = None
    password: tuple[SecretType, str] | None = None


class OptionalParams(BaseModel):
    auth_mode: str | None = None
    timeout: str | None = None
    in_downtime: str | None = None
    acknowledged: str | None = None
    track_downtimes: bool = False


class BiAggrParams(BaseModel):
    base_url: str
    aggregation_name: str
    credentials: Credentials
    optional: OptionalParams | None = None


def parse_credentials(raw_params: Mapping[str, object]) -> Credentials:
    credentials = raw_params["credentials"]
    if credentials == "automation":
        return Credentials(automation=True)
    if isinstance(credentials, tuple) and isinstance(credentials[1], tuple):
        return Credentials(user=credentials[1][0], password=credentials[1][1])
    raise ValueError("Invalid credentials parameters")


def parse_bi_aggr_params(raw_params: Mapping[str, object]) -> BiAggrParams:
    parsed_params = {
        "credentials": parse_credentials(raw_params),
        **{k: v for k, v in raw_params.items() if k != "credentials"},
    }
    return BiAggrParams.model_validate(parsed_params)


def check_bi_aggr_services(
    params: BiAggrParams, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    args: list[str | Secret] = ["-b", params.base_url, "-a", params.aggregation_name]
    if params.credentials.automation:
        args.append("--use-automation-user")
    elif params.credentials.user and params.credentials.password:
        # configured
        secret_type, secret_value = params.credentials.password
        args += [
            "-u",
            params.credentials.user,
            "-s",
            parse_secret(secret_type, secret_value),
        ]
    opt_params = params.optional
    if opt_params and opt_params.auth_mode:
        args += ["-m", opt_params.auth_mode]
    if opt_params and opt_params.timeout is not None:
        args += ["-t", opt_params.timeout]
    if opt_params and opt_params.in_downtime:
        args += ["--in-downtime", opt_params.in_downtime]
    if opt_params and opt_params.acknowledged:
        args += ["--acknowledged", opt_params.acknowledged]
    if opt_params and opt_params.track_downtimes:
        args += ["-r", "-n", host_config.name]
    description = f"Aggr {params.aggregation_name}"
    yield ActiveCheckCommand(service_description=description, command_arguments=args)


active_check_bi_aggr = ActiveCheckConfig(
    name="bi_aggr", parameter_parser=parse_bi_aggr_params, commands_function=check_bi_aggr_services
)
