#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand


class SpecialAgentConfig[ParsedParameters]:
    """
    This is an exact copy of the v1 version.
    We need a decoupled version here to be able to selectively
    discover alpha plugins.
    We must not inherit from v1 version, or vice versa.
    """

    def __init__(
        self,
        *,
        name: str,
        parameter_parser: Callable[[Mapping[str, object]], ParsedParameters],
        commands_function: Callable[[ParsedParameters, HostConfig], Iterable[SpecialAgentCommand]],
    ):
        self.name = name
        self._parameter_parser = parameter_parser
        self._commands_function = commands_function

    def __call__(
        self,
        parameters: Mapping[str, object],
        host_config: HostConfig,
    ) -> Iterable[SpecialAgentCommand]:
        return self._commands_function(self._parameter_parser(parameters), host_config)
