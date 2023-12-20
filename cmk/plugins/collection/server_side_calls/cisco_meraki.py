#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    parse_http_proxy,
    parse_secret,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)

from .utils import ProxyType, SecretType


class Params(BaseModel):
    api_key: tuple[SecretType, str]
    proxy: tuple[ProxyType, str | None] | None = None
    sections: Sequence[str] | None = None
    orgs: Sequence[str] | None = None


def agent_cisco_meraki_arguments(
    params: Params,
    host_config: HostConfig,
    http_proxies: Mapping[str, HTTPProxy],
) -> Iterator[SpecialAgentCommand]:
    secret_type, secret_value = params.api_key
    args: list[str | Secret] = [
        host_config.name,
        parse_secret(secret_type, secret_value),
    ]

    if params.proxy is not None:
        args += [
            "--proxy",
            parse_http_proxy(params.proxy, http_proxies),
        ]

    if params.sections is not None:
        args.append("--sections")
        args += params.sections

    if params.orgs is not None:
        args.append("--orgs")
        args += params.orgs

    yield SpecialAgentCommand(command_arguments=args)


special_agent_cisco_meraki = SpecialAgentConfig(
    name="cisco_meraki",
    parameter_parser=Params.model_validate,
    commands_function=agent_cisco_meraki_arguments,
)
