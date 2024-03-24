#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shlex
from collections.abc import Mapping, Sequence
from typing import Callable, Iterable, Literal, Protocol

import cmk.utils.config_warnings as config_warnings
from cmk.utils import password_store
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.servicename import ServiceName

from cmk.server_side_calls.v1 import Secret

CheckCommandArguments = Iterable[int | float | str | tuple[str, str, str]]


class SpecialAgentLegacyConfiguration(Protocol):
    args: Sequence[str]
    # None makes the stdin of subprocess /dev/null
    stdin: str | None


SpecialAgentInfoFunctionResult = (  # or check.
    str | Sequence[str | int | float | tuple[str, str, str]] | SpecialAgentLegacyConfiguration
)

InfoFunc = Callable[
    [Mapping[str, object], HostName, HostAddress | None], SpecialAgentInfoFunctionResult
]


class ActiveCheckError(Exception):  # or agent
    pass


def commandline_arguments(
    hostname: HostName,
    description: ServiceName | None,
    commandline_args: SpecialAgentInfoFunctionResult,
    passwords_from_store: Mapping[str, str] | None = None,
) -> str:
    """Commandline arguments for special agents or active checks."""

    if isinstance(commandline_args, str):
        return commandline_args

    # Some special agents also have stdin configured
    args = getattr(commandline_args, "args", commandline_args)

    if not isinstance(args, list):
        raise ActiveCheckError(
            "The check argument function needs to return either a list of arguments or a "
            "string of the concatenated arguments (Service: %s)." % (description)
        )

    return _prepare_check_command(
        args,
        hostname,
        description,
        password_store.load() if passwords_from_store is None else passwords_from_store,
    )


def _prepare_check_command(
    command_spec: CheckCommandArguments,
    hostname: HostName,
    description: ServiceName | None,
    passwords: Mapping[str, str],
) -> str:
    """Prepares a check command for execution by Checkmk

    In case a list is given it quotes element if necessary. It also prepares password store entries
    for the command line. These entries will be completed by the executed program later to get the
    password from the password store.
    """
    formatted: list[str | tuple[str, str, str]] = []
    for arg in command_spec:
        if isinstance(arg, (int, float)):
            formatted.append(str(arg))

        elif isinstance(arg, str):
            formatted.append(shlex.quote(arg))

        elif isinstance(arg, tuple) and len(arg) == 3:
            formatted.append(arg)

        else:
            raise ActiveCheckError(f"Invalid argument for command line: {arg!r}")

    return " ".join(
        password_store.hack.apply_password_hack(
            formatted, passwords, config_warnings.warn, _make_log_label(hostname, description)
        ),
    )


def replace_passwords(
    host_name: str,
    passwords: Mapping[str, str],
    arguments: Sequence[str | Secret],
    surrogated_secrets: Mapping[int, tuple[Literal["store", "password"], str]],
) -> str:
    formatted: list[str | tuple[str, str, str]] = []

    for arg in arguments:
        if isinstance(arg, str):
            formatted.append(shlex.quote(arg))
            continue

        secret_type, secret_value = surrogated_secrets[arg.id]

        match secret_type:
            case "password":
                formatted.append(shlex.quote(arg.format % secret_value))
            case "store":
                # fall back to old hack, for now
                formatted.append(("store", secret_value, arg.format))

    return " ".join(
        password_store.hack.apply_password_hack(
            formatted, passwords, config_warnings.warn, _make_log_label(host_name)
        ),
    )


def _make_log_label(host_name: str | None, description: ServiceName | None = None) -> str:
    if host_name and description:
        return f' used by service "{description}" on host "{host_name}"'
    if host_name:
        return f' used by host "{host_name}"'
    return ""


def replace_macros(string: str, macros: Mapping[str, str]) -> str:
    for macro, replacement in macros.items():
        string = string.replace(macro, str(replacement))
    return string
