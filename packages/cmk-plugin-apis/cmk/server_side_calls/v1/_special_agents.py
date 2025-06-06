#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from ._utils import HostConfig, Secret

_ParsedParameters = TypeVar("_ParsedParameters")


@dataclass(frozen=True, kw_only=True)
class SpecialAgentCommand:
    """
    Defines a special agent command

    Instances of this class will only be picked up by Checkmk if their names start with
    ``special_agent_``.

    One SpecialAgentCommand results in one call of the special agent.

    Command arguments will be shell-escaped during constructing the command line.
    That means that any string can be safely passed as a command argument.

    Args:
        command_arguments: Arguments that are passed to the special agent command-line interface
        stdin: String given to the special agent script's standard input.
                This should be used only in case the agent requires input bigger than the max
                command-line size, otherwise pass the input as a command argument.

    Example:
        >>> SpecialAgentCommand(
        ...     command_arguments=["--services", "logs", "errors", "stats"]
        ... )
        SpecialAgentCommand(command_arguments=['--services', 'logs', 'errors', 'stats'], stdin=None)
    """

    command_arguments: Sequence[str | Secret]
    stdin: str | None = None


class SpecialAgentConfig(Generic[_ParsedParameters]):
    """
    Defines a special agent

    Instances of this class will only be picked up by Checkmk if their names start
    with ``special_agent_``.

    One SpecialAgentConfig can result in multiple calls of the special agent.
    The executable will be searched for in the following three folders, in
    order of preference:

    * ``../../libexec``, relative to the file where the corresponding instance
      of :class:`SpecialAgentConfig` is discovered from (see example below)
    * ``local/share/check_mk/agents/special`` in the sites home directory
    * ``share/check_mk/agents/special`` in the sites home directory

    Args:
        name: Special agent name.
            Has to match special agent executable name without the prefix ``agent_``.
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
        ... ) -> Iterable[SpecialAgentCommand]:
        ...     args = ["--protocol", params.protocol, "--services", "logs", "errors", "stats"]
        ...     yield SpecialAgentCommand(command_arguments=args)

        >>> special_agent_example = SpecialAgentConfig(
        ...     name="smith",
        ...     parameter_parser=ExampleParams.model_validate,
        ...     commands_function=generate_example_commands,
        ... )

        If the above code belongs to the family "my_integration" and is put in the file
        ``local/lib/python3/cmk_addons/plugins/my_integration/server_side_calls/example.py``,
        the following executables will be searched for:

        * ``local/lib/python3/cmk_addons/plugins/my_integration/libexec/agent_smith``
        * ``local/share/check_mk/agents/special/agent_smith``
        * ``share/check_mk/agents/special/agent_smith``

        The first existing file will be used.
    """

    def __init__(
        self,
        *,
        name: str,
        parameter_parser: Callable[[Mapping[str, object]], _ParsedParameters],
        commands_function: Callable[[_ParsedParameters, HostConfig], Iterable[SpecialAgentCommand]],
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
