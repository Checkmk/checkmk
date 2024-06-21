#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from typing import Literal, NotRequired, TypedDict

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    replace_macros,
)


def check_by_ssh_description(params):
    settings = params[1]
    if "description" in settings:
        return settings["description"]
    return "check_by_ssh %s" % params[0]


class _SSHSettings(TypedDict):
    description: NotRequired[str]
    hostname: NotRequired[str]
    port: NotRequired[int]
    ip_version: NotRequired[Literal["ipv4", "ipv6"]]
    timeout: NotRequired[int]
    logname: NotRequired[str]
    identity: NotRequired[str]
    accept_new_host_keys: NotRequired[Literal[True]]


_SSHOptions = tuple[str, _SSHSettings]


# TODO: add proper parsing. un-nest the parameters.
def _check_by_ssh_parser(params: Mapping[str, object]) -> _SSHOptions:
    ssh_options = params["options"]
    assert isinstance(ssh_options, tuple)
    return ssh_options


def check_by_ssh_command(
    params: _SSHOptions,
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    args = []
    settings = params[1]
    if "hostname" in settings:
        args += ["-H", replace_macros(settings["hostname"], host_config.macros)]
    else:
        args += ["-H", host_config.primary_ip_config.address]

    args += ["-C", "%s" % replace_macros(params[0], host_config.macros)]
    if "port" in settings:
        args += ["-p", str(settings["port"])]
    if "ip_version" in settings:
        if settings["ip_version"] == "ipv4":
            args.append("-4")
        else:
            args.append("-6")

    if settings.get("accept_new_host_keys", False):
        args += ["-o", "StrictHostKeyChecking=accept-new"]
    if "timeout" in settings:
        args += ["-t", str(settings["timeout"])]
    if "logname" in settings:
        args += ["-l", settings["logname"]]
    if "identity" in settings:
        args += ["-i", settings["identity"]]

    description = replace_macros(check_by_ssh_description(params), host_config.macros)
    yield ActiveCheckCommand(service_description=description, command_arguments=args)


active_check_by_ssh = ActiveCheckConfig(
    name="by_ssh", parameter_parser=_check_by_ssh_parser, commands_function=check_by_ssh_command
)
