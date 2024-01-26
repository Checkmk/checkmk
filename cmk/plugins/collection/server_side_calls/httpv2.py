#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Iterator, Mapping, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig, HTTPProxy


class Endpoint(BaseModel):
    name: str
    protocol_prefix: bool
    url: str


HTTPParams = Sequence[Endpoint]


def parse_http_params(raw_params: Mapping[str, object]) -> HTTPParams:
    assert isinstance(raw_params["endpoints"], list)
    return [
        Endpoint.model_validate(
            {
                "name": endpoint["service_name"]["name"],
                "protocol_prefix": endpoint["service_name"]["prefix"] == "auto",
                "url": endpoint["url"],
            }
        )
        for endpoint in raw_params["endpoints"]
    ]


def generate_http_services(
    params: HTTPParams, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    for endpoint in params:
        protocol = "HTTPS" if endpoint.url.startswith("https://") else "HTTP"
        prefix = f"{protocol} " if endpoint.protocol_prefix else ""
        yield ActiveCheckCommand(
            service_description=f"{prefix}{endpoint.name}",
            command_arguments=["-u", endpoint.url],
        )


active_check_httpv2 = ActiveCheckConfig(
    name="httpv2",
    parameter_parser=parse_http_params,
    commands_function=generate_http_services,
)
