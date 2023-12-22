#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    HTTPProxy,
    IPAddressFamily,
    parse_secret,
    Secret,
    StoredSecret,
)


class ExampleParams(BaseModel):
    protocol: str
    user: str
    password: tuple[Literal["store", "password"], str]


def parse_example_params(params: Mapping[str, object]) -> ExampleParams:
    return ExampleParams.model_validate(params)


def generate_example_commands(
    params: ExampleParams,
    _host_config: HostConfig,
    _http_proxies: Mapping[str, HTTPProxy],
) -> Iterator[ActiveCheckCommand]:
    args: Sequence[str | Secret] = [
        "-p",
        params.protocol,
        "-u",
        params.user,
        "-s",
        parse_secret(params.password),
    ]
    yield ActiveCheckCommand(service_description="Example", command_arguments=args)


active_check_example = ActiveCheckConfig(
    name="example",
    parameter_parser=parse_example_params,
    commands_function=generate_example_commands,
)


def test_active_check_config() -> None:
    host_config = HostConfig(
        name="hostname",
        address="0.0.0.1",
        alias="host_alias",
        ip_family=IPAddressFamily.IPV4,
        ipv4address="0.0.0.1",
    )
    params = {
        "protocol": "HTTP",
        "user": "example_user",
        "password": ("store", "stored_password_id"),
    }

    parsed_params = active_check_example.parameter_parser(params)
    commands = list(active_check_example.commands_function(parsed_params, host_config, {}))

    assert len(commands) == 1
    assert commands[0] == ActiveCheckCommand(
        service_description="Example",
        command_arguments=[
            "-p",
            "HTTP",
            "-u",
            "example_user",
            "-s",
            StoredSecret(value="stored_password_id", format="%s"),
        ],
    )
