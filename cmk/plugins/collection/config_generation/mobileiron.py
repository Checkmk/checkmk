#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping, Sequence

from pydantic import BaseModel, Field

from cmk.config_generation.v1 import (
    get_http_proxy,
    get_secret_from_params,
    HostConfig,
    HTTPProxy,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)

from .utils import ProxyType, SecretType


class MobileIronParams(BaseModel):
    username: str
    password: tuple[SecretType, str]
    proxy: tuple[ProxyType, str | None] | None = None
    partition: Sequence[str]
    key_fields: tuple[str] | tuple[str, str] = Field(..., alias="key-fields")
    android_regex: Sequence[str] = Field(alias="android-regex", default_factory=list)
    ios_regex: Sequence[str] = Field(alias="ios-regex", default_factory=list)
    other_regex: Sequence[str] = Field(alias="other-regex", default_factory=list)


def generate_mobileiron_command(
    params: MobileIronParams, host_config: HostConfig, http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "-u",
        params.username,
        "-p",
        get_secret_from_params(*params.password),
        "--partition",
        ",".join(params.partition),
        "--hostname",
        host_config.name,
    ]
    if params.proxy:
        args += [
            "--proxy",
            get_http_proxy(*params.proxy, http_proxies),
        ]

    for expression in params.android_regex:
        args.append(f"--android-regex={expression}")

    for expression in params.ios_regex:
        args.append(f"--ios-regex={expression}")

    for expression in params.other_regex:
        args.append(f"--other-regex={expression}")

    for key_field in params.key_fields:
        args.append("--key-fields")
        args.append(key_field)

    yield SpecialAgentCommand(command_arguments=args)


special_agent_mobileiron = SpecialAgentConfig(
    name="mobileiron",
    parameter_parser=MobileIronParams.model_validate,
    commands_function=generate_mobileiron_command,
)
