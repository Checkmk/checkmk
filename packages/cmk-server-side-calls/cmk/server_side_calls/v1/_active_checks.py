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
class ActiveCheckCommand:
    """
    Defines an active check command

    One ActiveCheckCommand results in one Checkmk service.

    Args:
        service_description: Description of the created service
        command_arguments: Arguments that are passed to the active checks command-line interface

    Example:
        >>> from cmk.server_side_calls.v1 import StoredSecret

        >>> ActiveCheckCommand(
        ...     service_description="Example description",
        ...     command_arguments=[
        ...         "--user",
        ...         "example-user",
        ...         "--password",
        ...         StoredSecret("stored_password_id")
        ...     ]
        ...     )
        ActiveCheckCommand(service_description='Example description', command_arguments=['--user', \
'example-user', '--password', StoredSecret(value='stored_password_id', format='%s')])
    """

    service_description: str
    command_arguments: Sequence[str | Secret]


@dataclass(frozen=True)
class ActiveCheckConfig(Generic[_ParsedParameters]):
    """
    Defines an active check

    One ActiveCheckConfig can create multiple Checkmk services.

    Args:
        name: Active check name. Has to match active check executable name without the prefix
            ´check_´.
        parameter_parser: Translates the raw configured parameters into a validated data structure.
                The result of the function will be passed as an argument to the command_function.
                If you don't want to parse your parameters, use the noop_parser.
        commands_function: Computes the active check commands from the configured parameters

    Example:

        >>> from cmk.server_side_calls.v1 import noop_parser

        >>> def generate_example_commands(
        ...     params: Mapping[str, object],
        ...     host_config: HostConfig,
        ...     http_proxies: Mapping[str, HTTPProxy]
        ... ) -> Iterable[ActiveCheckCommand]:
        ...     args = ["--service", str(params["service"])]
        ...     yield ActiveCheckCommand(
        ...         service_description="Example description",
        ...         command_arguments=args
        ...         )

        >>> active_check_example = ActiveCheckConfig(
        ...     name="example",
        ...     parameter_parser=noop_parser,
        ...     commands_function=generate_example_commands,
        ... )
    """

    name: str
    parameter_parser: Callable[[Mapping[str, object]], _ParsedParameters]
    commands_function: Callable[
        [_ParsedParameters, HostConfig, Mapping[str, HTTPProxy]], Iterable[ActiveCheckCommand]
    ]
