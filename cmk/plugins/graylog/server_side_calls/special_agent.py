#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# {
#     'port': 9000,
#     'password': 'yeah',
#     'sections': ['jvm', 'cluster_health', 'failures'],
#     'since': 30,
#     'user': 'hell',
#     'display_node_details': 'node',
#     'display_sidecar_details': 'sidecar',
#     'display_source_details': 'source',
# }


from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret


class Params(BaseModel):
    instance: str
    user: str
    password: Secret
    protocol: str
    port: int | None = None
    since: float
    source_since: float | None = None
    alerts_since: float | None = None
    events_since: float | None = None
    sections: Sequence[str]
    display_node_details: str
    display_sidecar_details: str
    display_source_details: str


def commands_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = [
        "--proto",
        params.protocol,
        "--sections",
        ",".join(params.sections),
        "--since",
        f"{params.since:.0f}",
        "--user",
        params.user,
        "--password",
        params.password.unsafe(),
        "--display_node_details",
        params.display_node_details,
        "--display_sidecar_details",
        params.display_sidecar_details,
        "--display_source_details",
        params.display_source_details,
    ]

    if params.port:
        command_arguments += ["--port", f"{params.port}"]

    if params.source_since:
        command_arguments += ["--source_since", f"{params.source_since:.0f}"]

    if params.alerts_since:
        command_arguments += ["--alerts_since", f"{params.alerts_since:.0f}"]

    if params.events_since:
        command_arguments += ["--events_since", f"{params.events_since:.0f}"]

    command_arguments.append(params.instance)

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_graylog = SpecialAgentConfig(
    name="graylog",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
