#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class _Params(BaseModel, frozen=True):
    url: str
    vhm_id: str
    api_token: str
    client_id: str
    client_secret: Secret
    redirect_url: str


def _commands_function(
    params: _Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    yield SpecialAgentCommand(
        command_arguments=[
            params.url,
            params.vhm_id,
            params.api_token,
            params.client_id,
            params.client_secret.unsafe(),
            params.redirect_url,
        ]
    )


special_agent_hivemanager_ng = SpecialAgentConfig(
    name="hivemanager_ng",
    parameter_parser=_Params.model_validate,
    commands_function=_commands_function,
)
