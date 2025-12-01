#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
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


class Params(BaseModel, frozen=True):
    svc_item: str
    hostname: str | None = None
    protocol: Literal["http", "https"] | None = None
    user: str | None = None
    password: Secret | None = None
    port: int | None = None
    index: list[str] | None = None
    pattern: str
    fieldname: list[str] | None = None
    timerange: int
    upper_log_count_thresholds: (
        tuple[Literal["fixed"], tuple[int, int]] | tuple[Literal["no_levels"], None] | None
    ) = None
    lower_log_count_thresholds: (
        tuple[Literal["fixed"], tuple[int, int]] | tuple[Literal["no_levels"], None] | None
    ) = None
    verify_tls_cert: bool


def commands_function(
    params: Params,
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    args: list[str | Secret] = ["-q", params.pattern, "-t", str(params.timerange)]

    if params.protocol is not None:
        args += ["-P", params.protocol]
    if params.user is not None:
        args += ["-u", params.user]
    if params.password is not None:
        args += ["--password-id", params.password]
    if params.port is not None:
        args += ["-p", str(params.port)]
    if params.index:
        args += ["-i", " ".join(params.index)]
    if params.fieldname is not None:
        args += ["-f", " ".join(params.fieldname)]
    if (
        params.upper_log_count_thresholds is not None
        and params.upper_log_count_thresholds[0] == "fixed"
    ):
        warn, crit = params.upper_log_count_thresholds[1]
        args += ["--warn-upper-log-count=%d" % warn, "--crit-upper-log-count=%d" % crit]
    if (
        params.lower_log_count_thresholds is not None
        and params.lower_log_count_thresholds[0] == "fixed"
    ):
        warn, crit = params.lower_log_count_thresholds[1]
        args += ["--warn-lower-log-count=%d" % warn, "--crit-lower-log-count=%d" % crit]

    if params.hostname is not None:
        args += ["-H", replace_macros(params.hostname, host_config.macros)]
    else:
        args += ["-H", host_config.primary_ip_config.address]

    if not params.verify_tls_cert:
        args += ["--no-verify-tls-cert"]

    item = replace_macros(params.svc_item, host_config.macros)
    yield ActiveCheckCommand(
        service_description=f"Elasticsearch Query {item}", command_arguments=args
    )


active_check_config = ActiveCheckConfig(
    name="elasticsearch_query",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
