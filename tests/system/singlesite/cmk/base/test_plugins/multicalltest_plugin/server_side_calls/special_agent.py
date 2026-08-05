#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# A throw-away special agent that yields *three* command lines.  It is copied
# into a test site to play the role of a third-party plugin (SUP-29815).

from collections.abc import Iterator, Mapping

from cmk.server_side_calls.v1 import (
    HostConfig,
    noop_parser,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def _agent_arguments(
    params: Mapping[str, object], host_config: HostConfig
) -> Iterator[SpecialAgentCommand]:
    yield SpecialAgentCommand(command_arguments=["--id", "one"])
    yield SpecialAgentCommand(command_arguments=["--id", "two"])
    yield SpecialAgentCommand(command_arguments=["--id", "three"])


special_agent_multicalltest = SpecialAgentConfig(
    name="multicalltest",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
