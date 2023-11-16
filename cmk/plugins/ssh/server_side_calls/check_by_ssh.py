#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from typing import Any

from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig, HTTPProxy


def check_by_ssh_description(params):
    settings = params[1]
    if "description" in settings:
        return settings["description"]
    return "check_by_ssh %s" % params[0]


_SSHOptions = tuple[str, dict[str, Any]]


def _check_by_ssh_parser(params: Mapping[str, object]) -> _SSHOptions:
    ssh_options = params["options"]
    assert isinstance(ssh_options, tuple)
    return ssh_options


def check_by_ssh_command(
    params: _SSHOptions,
    host_config: HostConfig,
    _http_proxies: Mapping[str, HTTPProxy],
) -> Iterator[ActiveCheckCommand]:
    args = []
    settings = params[1]
    if "hostname" in settings:
        args += ["-H", settings["hostname"]]
    else:
        args += ["-H", host_config.address]

    args += ["-C", "%s" % params[0]]
    if "port" in settings:
        args += ["-p", settings["port"]]
    if "ip_version" in settings:
        if settings["ip_version"] == "ipv4":
            args.append("-4")
        else:
            args.append("-6")

    if settings.get("accept_new_host_keys", False):
        args += ["-o", "StrictHostKeyChecking=accept-new"]
    if "timeout" in settings:
        args += ["-t", settings["timeout"]]
    if "logname" in settings:
        args += ["-l", settings["logname"]]
    if "identity" in settings:
        args += ["-i", settings["identity"]]

    yield ActiveCheckCommand(
        service_description=check_by_ssh_description(params), command_arguments=args
    )


active_check_by_ssh = ActiveCheckConfig(
    name="by_ssh", parameter_parser=_check_by_ssh_parser, commands_function=check_by_ssh_command
)
