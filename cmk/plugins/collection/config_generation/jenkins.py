#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Iterator, Mapping, Sequence

from pydantic import BaseModel

from cmk.config_generation.v1 import (
    get_secret_from_params,
    HostConfig,
    HTTPProxy,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)

from .utils import SecretType


class JenkinsParams(BaseModel):
    user: str
    password: tuple[SecretType, str]
    protocol: str
    instance: str
    port: int | None = None
    sections: Sequence[str] = []


def parse_jenkins_params(raw_params: Mapping[str, object]) -> JenkinsParams:
    return JenkinsParams.model_validate(raw_params)


def agent_jenkins_config(
    params: JenkinsParams,
    _host_config: HostConfig,
    _http_proxies: Mapping[str, HTTPProxy],
) -> Iterator[SpecialAgentCommand]:
    secret_type, secret_value = params.password
    args: list[str | Secret] = [
        "-P",
        params.protocol,
        "-u",
        params.user,
        "-s",
        get_secret_from_params(secret_type, secret_value),
    ]

    if params.sections:
        args += ["-m", " ".join(params.sections)]

    if params.port:
        args += ["-p", str(params.port)]

    args.append(params.instance)

    yield SpecialAgentCommand(command_arguments=args)


special_agent_jenkins = SpecialAgentConfig(
    name="jenkins", parameter_parser=parse_jenkins_params, commands_function=agent_jenkins_config
)
