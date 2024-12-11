#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""server side component to create the special agent call"""
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# License: GNU General Public License v2

from collections.abc import Iterator
from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class Params(BaseModel):
    """params validator"""
    user: str | None = None
    password: Secret | None = None
    port: int | None = None
    proto: tuple[str, str | None] = ("https", None)
    sections: list | None = None
    disabled_sections: list | None = None
    cached_sections: dict | None = None
    timeout: int | None = None
    retries: int | None = None
    debug: bool | None = None


def _agent_redfish_arguments(
    params: Params, host_config: HostConfig
) -> Iterator[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = []
    if params.user is not None:
        command_arguments += ["-u", params.user]
    if params.password is not None:
        command_arguments += ["--password-id", params.password]
    if params.port is not None:
        command_arguments += ["-p", str(params.port)]
    if params.proto is not None:
        command_arguments += ["-P", params.proto[0]]
    if params.sections is not None:
        command_arguments += ["-m", ",".join(params.sections)]
    if params.disabled_sections is not None:
        command_arguments += ["-n", ",".join(params.disabled_sections)]
    if params.timeout is not None:
        command_arguments += ["--timeout", str(params.timeout)]
    if params.retries is not None:
        command_arguments += ["--retries", str(params.retries)]
    if params.debug:
        command_arguments += ["--debug"]
    if params.cached_sections is not None:
        cache_sections = []
        for n, m in params.cached_sections.items():
            cache_sections.append(f"{n}-{m}")
        command_arguments += ["-c", ",".join(cache_sections)]

    command_arguments.append(host_config.primary_ip_config.address or host_config.name)
    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_redfish = SpecialAgentConfig(
    name="redfish",
    parameter_parser=Params.model_validate,
    commands_function=_agent_redfish_arguments,
)

special_agent_redfish_power = SpecialAgentConfig(
    name="redfish_power",
    parameter_parser=Params.model_validate,
    commands_function=_agent_redfish_arguments,
)
