#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class ExampleParams(BaseModel):
    protocol: str
    user: str
    password: Secret


def parse_example_params(params: Mapping[str, object]) -> ExampleParams:
    return ExampleParams.model_validate(params)


def generate_example_commands(
    params: ExampleParams,
    _host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    yield SpecialAgentCommand(
        command_arguments=(
            "-p",
            params.protocol,
            "-u",
            params.user,
            "-s",
            params.password,
        )
    )


special_agent_example = SpecialAgentConfig(
    name="example",
    parameter_parser=parse_example_params,
    commands_function=generate_example_commands,
)


def test_active_check_config() -> None:
    host_config = HostConfig(name="hostname")

    params = {
        "protocol": "HTTP",
        "user": "example_user",
        "password": Secret(42),
    }

    commands = list(special_agent_example(params, host_config))

    assert len(commands) == 1
    assert commands[0] == SpecialAgentCommand(
        command_arguments=(
            "-p",
            "HTTP",
            "-u",
            "example_user",
            "-s",
            Secret(42),
        ),
    )
