#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from ._utils import HostConfig, HTTPProxy, Secret

_ParsedParameters = TypeVar("_ParsedParameters")


@dataclass(frozen=True)
class SpecialAgentCommand:
    """
    Defines a special agent command

    One SpecialAgentCommand results in one call of the special agent.

    Args:
        command_arguments: Arguments that are passed to the special agent command-line interface
        stdin: String given to the special agent script's standard input.
                This should be used only in case the agent requires input bigger than the max
                command-line size, otherwise pass the input as a command argument.

    Example:
        >>> SpecialAgentCommand(
        ...     command_arguments=["--services", "logs", "errors", "stats"]
        ...     )
        SpecialAgentCommand(command_arguments=['--services', 'logs', 'errors', 'stats'], stdin=None)
    """

    command_arguments: Sequence[str | Secret]
    stdin: str | None = None


@dataclass(frozen=True)
class SpecialAgentConfig(Generic[_ParsedParameters]):
    """
    Defines a special agent

    One SpecialAgentConfig can result in multiple calls of the special agent.

    Args:
        name: Special agent name. Has to match special agent executable name without
                the prefix ´agent_´.
        parameter_parser: Translates the raw configured parameters into a validated data structure.
                        The result of the function will be passed as an argument to
                        the command_function. If you don't want to parse your parameters,
                        use the noop_parser.
        commands_function: Computes the special agent commands from the configured parameters

    Example:

        >>> from pydantic import BaseModel

        >>> class ExampleParams(BaseModel):
        ...     protocol: str

        >>> def generate_example_commands(
        ...     params: ExampleParams,
        ...     host_config: HostConfig,
        ...     http_proxies: Mapping[str, HTTPProxy]
        ... ) -> Iterable[SpecialAgentCommand]:
        ...     args = ["--protocol", params.protocol, "--services", "logs", "errors", "stats"]
        ...     yield SpecialAgentCommand(command_arguments=args)

        >>> special_agent_example = SpecialAgentConfig(
        ...     name="example",
        ...     parameter_parser=ExampleParams.model_validate,
        ...     commands_function=generate_example_commands,
        ... )
    """

    name: str
    parameter_parser: Callable[[Mapping[str, object]], _ParsedParameters]
    commands_function: Callable[
        [_ParsedParameters, HostConfig, Mapping[str, HTTPProxy]], Iterable[SpecialAgentCommand]
    ]
