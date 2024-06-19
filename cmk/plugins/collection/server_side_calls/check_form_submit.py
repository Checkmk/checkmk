#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    replace_macros,
)


class UrlParams(BaseModel):
    hosts: list[str] | None = None
    uri: str | None = None
    port: int | None = None
    tls_configuration: str | None = None
    timeout: int | None = None
    expect_regex: str | None = None
    form_name: str | None = None
    query: str | None = None
    num_succeeded: tuple[int, int] | None = None


class Params(BaseModel):
    name: str
    url_details: UrlParams


def commands_function(params: Params, host_config: HostConfig) -> Iterator[ActiveCheckCommand]:
    details = params.url_details
    args = []

    if details.hosts:
        args += [*[replace_macros(h, host_config.macros) for h in details.hosts]]
    else:
        args += [host_config.primary_ip_config.address]

    if details.port:
        args += ["--port", str(details.port)]

    if details.uri:
        args += ["--uri", replace_macros(details.uri, host_config.macros)]

    if details.tls_configuration:
        args += ["--tls_configuration", details.tls_configuration]

    if details.timeout:
        args += ["--timeout", str(details.timeout)]

    if details.expect_regex:
        args += ["--expected_regex", details.expect_regex]

    if details.form_name:
        form_name = replace_macros(details.form_name, host_config.macros)
        args += ["--form_name", form_name]

    if details.query:
        args += ["--query_params", details.query]

    if details.num_succeeded:
        args += ["--levels", *(str(e) for e in details.num_succeeded)]

    name = replace_macros(params.name, host_config.macros)
    yield ActiveCheckCommand(service_description=f"FORM {name}", command_arguments=args)


active_check_config = ActiveCheckConfig(
    name="form_submit",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
