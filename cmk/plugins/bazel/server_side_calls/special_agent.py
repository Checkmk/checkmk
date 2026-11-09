#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

from pydantic import BaseModel, model_validator

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class Params(BaseModel):
    user: str | None = None
    password: Secret | None = None
    port: int | None = None
    protocol: str | None = None
    verify_cert: bool

    @model_validator(mode="before")
    @classmethod
    def _read_unmigrated_cert_check_key(cls, data: object) -> object:
        # A central site on an older 2.5.0 patch release still sends the unmigrated
        # key, and the remote site does not run cmk-update-config within a minor
        # version. The old value already means "verify", so read it as is.
        if not isinstance(data, dict) or "no_cert_check" not in data:
            return data
        migrated = {k: v for k, v in data.items() if k != "no_cert_check"}
        migrated["verify_cert"] = data["no_cert_check"]
        return migrated


def generate_bazel_cache_command(
    params: Params, host_config: HostConfig
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = ["--host", host_config.name]

    if params.user is not None:
        args += ["--user", params.user]
    if params.password is not None:
        args += ["--password-id", params.password]
    if params.port is not None:
        args += ["--port", str(params.port)]
    if params.protocol is not None:
        args += ["--protocol", params.protocol]
    if not params.verify_cert:
        args += ["--no-cert-check"]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_bazel_cache = SpecialAgentConfig(
    name="bazel_cache",
    parameter_parser=Params.model_validate,
    commands_function=generate_bazel_cache_command,
)
