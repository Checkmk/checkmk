#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Iterator, Mapping

from pydantic import BaseModel

from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig, HTTPProxy


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


def commands_function(
    params: Params, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    details = params.url_details
    args = []

    if details.hosts:
        args += [*details.hosts]
    elif host_config.address:
        args += [host_config.address]
    else:
        raise ValueError("No IP address available")

    if details.port:
        args += ["--port", str(details.port)]

    if details.uri:
        args += ["--uri", details.uri]

    if details.tls_configuration:
        args += ["--tls_configuration", details.tls_configuration]

    if details.timeout:
        args += ["--timeout", str(details.timeout)]

    if details.expect_regex:
        args += ["--expected_regex", details.expect_regex]

    if details.form_name:
        args += ["--form_name", details.form_name]

    if details.query:
        args += ["--query_params", details.query]

    if details.num_succeeded:
        args += ["--levels", *(str(e) for e in details.num_succeeded)]

    yield ActiveCheckCommand(
        service_description=f"FORM {details.form_name}", command_arguments=args
    )


active_check_config = ActiveCheckConfig(
    name="form_submit",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
