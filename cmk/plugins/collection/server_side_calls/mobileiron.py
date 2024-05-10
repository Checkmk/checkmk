#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Sequence

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    EnvProxy,
    HostConfig,
    NoProxy,
    replace_macros,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
    URLProxy,
)

KEY_FIELD_MAP = {
    "serialNumber": ("serialNumber",),
    "emailAddress": ("emailAddress",),
    "emailAddress_serialNumber": ("emailAddress", "serialNumber"),
    "deviceModel_serialNumber": ("deviceModel", "serialNumber"),
    "uid": ("uid",),
    "uid_serialNumber": ("uid", "serialNumber"),
    "guid": ("guid",),
}


class MobileIronParams(BaseModel):
    username: str
    password: Secret
    proxy: URLProxy | EnvProxy | NoProxy | None = None
    partition: Sequence[str]
    key_fields: str
    android_regex: Sequence[str] = Field(default_factory=list)
    ios_regex: Sequence[str] = Field(default_factory=list)
    other_regex: Sequence[str] = Field(default_factory=list)


def generate_mobileiron_command(
    params: MobileIronParams,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    partitions = [replace_macros(p, host_config.macros) for p in params.partition]
    args: list[str | Secret] = [
        "-u",
        params.username,
        "-p",
        params.password.unsafe(),
        "--partition",
        ",".join(partitions),
        "--hostname",
        host_config.name,
    ]

    match params.proxy:
        case URLProxy(url=url):
            args += ["--proxy", url]
        case EnvProxy():
            args += ["--proxy", "FROM_ENVIRONMENT"]
        case NoProxy():
            args += ["--proxy", "NO_PROXY"]

    for expression in params.android_regex:
        args.append(f"--android-regex={expression}")

    for expression in params.ios_regex:
        args.append(f"--ios-regex={expression}")

    for expression in params.other_regex:
        args.append(f"--other-regex={expression}")

    for key_field in KEY_FIELD_MAP[params.key_fields]:
        args.append("--key-fields")
        args.append(key_field)

    yield SpecialAgentCommand(command_arguments=args)


special_agent_mobileiron = SpecialAgentConfig(
    name="mobileiron",
    parameter_parser=MobileIronParams.model_validate,
    commands_function=generate_mobileiron_command,
)
