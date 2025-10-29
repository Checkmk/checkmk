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
class ActiveCheckCommand:
    """
    Defines an active check command

    One ActiveCheckCommand results in one Checkmk service.

    Command arguments will be shell-escaped during constructing the command line.
    That means that any string can be safely passed as a command argument.

    Args:
        service_description: Description of the created service
        command_arguments: Arguments that are passed to the active checks command-line interface

    Example:
        >>> from cmk.server_side_calls.v1 import Secret

        >>> ActiveCheckCommand(
        ...     service_description="Example description",
        ...     command_arguments=[
        ...         "--user",
        ...         "example-user",
        ...         "--password",
        ...         Secret(0)
        ...     ]
        ... )
        ActiveCheckCommand(service_description='Example description', command_arguments=['--user', \
'example-user', '--password', Secret(id=0, format='%s', pass_safely=True)])
    """

    service_description: str
    command_arguments: Sequence[str | Secret]


class ActiveCheckConfig(Generic[_ParsedParameters]):
    """
    Defines an active check

    Instances of this class will only be picked up by Checkmk if their names start with
    ``active_check_``.

    One ActiveCheckConfig can create multiple Checkmk services.
    The executable will be searched for in the following three folders, in
    order of preference:

    * ``../../libexec``, relative to the file where the corresponding instance
      of :class:`ActiveCheckConfig` is discovered from (see example below)
    * ``local/lib/nagios/plugins`` in the sites home directory
    * ``lib/nagios/plugins`` in the sites home directory


    Args:
        name: Active check name.
            Has to match active check executable name without the prefix ``check_``.
        parameter_parser: Translates the raw configured parameters into a validated data structure.
                The result of the function will be passed as an argument to the command_function.
                If you don't want to parse your parameters, use the noop_parser.
        commands_function: Computes the active check commands from the configured parameters

    Example:

        >>> from cmk.server_side_calls.v1 import noop_parser

        >>> def generate_example_commands(
        ...     params: Mapping[str, object],
        ...     host_config: HostConfig,
        ... ) -> Iterable[ActiveCheckCommand]:
        ...     args = ["--service", str(params["service"])]
        ...     yield ActiveCheckCommand(
        ...         service_description="Example description",
        ...         command_arguments=args
        ...         )

        >>> active_check_example = ActiveCheckConfig(
        ...     name="norris",
        ...     parameter_parser=noop_parser,
        ...     commands_function=generate_example_commands,
        ... )

        If the above code belongs to the family "my_integration" and is put in the file
        ``local/lib/python3/cmk_addons/plugins/my_integration/server_side_calls/example.py``,
        the following executables will be searched for:

        * ``local/lib/python3/cmk_addons/plugins/my_integration/libexec/check_norris``
        * ``local/lib/nagios/plugins/check_norris``
        * ``lib/nagios/plugins/check_norris``

        The first existing file will be used.
    """

    def __init__(
        self,
        *,
        name: str,
        parameter_parser: Callable[[Mapping[str, object]], _ParsedParameters],
        commands_function: Callable[[_ParsedParameters, HostConfig], Iterable[ActiveCheckCommand]],
    ):
        self.name = name
        self._parameter_parser = parameter_parser
        self._commands_function = commands_function

    def __call__(
        self,
        parameters: Mapping[str, object],
        host_config: HostConfig,
    ) -> Iterable[ActiveCheckCommand]:
        return self._commands_function(
            self._parameter_parser(parameters),
            host_config,
        )
