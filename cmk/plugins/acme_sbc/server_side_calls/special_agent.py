#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from cmk.server_side_calls.v1 import (
    HostConfig,
    noop_parser,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def _commands_function(
    params: Mapping[str, object],
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    yield SpecialAgentCommand(command_arguments=[host_config.name])


special_agent_acme_sbc = SpecialAgentConfig(
    name="acme_sbc",
    parameter_parser=noop_parser,
    commands_function=_commands_function,
)
