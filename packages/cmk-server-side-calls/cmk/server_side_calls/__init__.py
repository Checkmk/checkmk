#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Server-side Calls API is used for active check and special agent plug-in development.
It provides a way to specify subprocess commands that are used to call special agents
and active checks from the configured rules.

Each plug-in can create multiple commands. One command results in one call of an active check
or special agent script. For active checks, one command will result in exactly one service.

Quick Guide
===========
This section offers a quick introduction to creating your own commands.

Special agent
-------------
    * Create a SpecialAgentConfig object
    * Variable name of a SpecialAgentConfig object has to start with the `special_agent_` prefix
    * The file with the plug-in has to be placed in the `server_side_calls` folder


    >>> from collections.abc import Iterator, Mapping, Sequence
    ...
    >>> from pydantic import BaseModel
    ...
    >>> from cmk.server_side_calls.v1 import (
    ...     HostConfig,
    ...     Secret,
    ...     SpecialAgentCommand,
    ...     SpecialAgentConfig,
    ... )
    ...
    ...
    >>> class ExampleParams(BaseModel):
    ...     protocol: str
    ...     user: str
    ...     password: Secret
    ...
    ...
    >>> def generate_example_commands(
    ...     params: ExampleParams,
    ...     _host_config: HostConfig,
    ... ) -> Iterator[SpecialAgentCommand]:
    ...     args: Sequence[str | Secret] = [
    ...         "-p",
    ...         params.protocol,
    ...         "-u",
    ...         params.user,
    ...         "-s",
    ...        params.password,
    ...     ]
    ...
    ...     yield SpecialAgentCommand(command_arguments=args)
    ...
    ...
    >>> special_agent_example = SpecialAgentConfig(
    ...     name="example",
    ...     parameter_parser=ExampleParams.model_validate,
    ...     commands_function=generate_example_commands,
    ... )



Active check
------------
    * Create a ActiveCheckConfig object
    * Variable name of a ActiveCheckConfig object has to start with the `active_check_` prefix
    * The file with the plug-in has to be placed in the `server_side_calls` folder


    >>> from collections.abc import Iterator, Mapping, Sequence
    ...
    >>> from pydantic import BaseModel
    ...
    >>> from cmk.server_side_calls.v1 import (
    ...     ActiveCheckCommand,
    ...     ActiveCheckConfig,
    ...     HostConfig,
    ...     Secret,
    ... )
    ...
    ...
    >>> class ExampleParams(BaseModel):
    ...     protocol: str
    ...     user: str
    ...     password: Secret
    ...
    ...
    >>> def generate_example_commands(
    ...     params: ExampleParams,
    ...     _host_config: HostConfig,
    ... ) -> Iterator[ActiveCheckCommand]:
    ...     args: Sequence[str | Secret] = [
    ...         "-p",
    ...         params.protocol,
    ...         "-u",
    ...         params.user,
    ...         "-s",
    ...         params.password,
    ...     ]
    ...
    ...     yield ActiveCheckCommand(service_description="Example", command_arguments=args)
    ...
    ...
    >>> active_check_example = ActiveCheckConfig(
    ...     name="example",
    ...     parameter_parser=ExampleParams.model_validate,
    ...     commands_function=generate_example_commands,
    ... )
"""
