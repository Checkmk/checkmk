#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shlex
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Protocol

from cmk.utils import config_warnings, password_store
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

InfoFunc = Callable[[object, HostName, HostAddress | None], SpecialAgentInfoFunctionResult]


class ActiveCheckError(Exception):  # or agent
    pass


def commandline_arguments(
    hostname: HostName,
    description: ServiceName | None,
    commandline_args: SpecialAgentInfoFunctionResult,
    passwords: Mapping[str, str],
    password_store_file: Path,
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

    return _prepare_check_command(args, hostname, description, passwords, password_store_file)


def _prepare_check_command(
    command_spec: CheckCommandArguments,
    hostname: HostName,
    description: ServiceName | None,
    passwords: Mapping[str, str],
    password_store_file: Path,
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
            formatted,
            passwords,
            password_store_file,
            config_warnings.warn,
            _make_log_label(hostname, description),
        ),
    )


def replace_passwords(
    host_name: str,
    arguments: Sequence[str | Secret],
    passwords: Mapping[str, str],
    password_store_file: Path,
    surrogated_secrets: Mapping[int, str],
    *,
    apply_password_store_hack: bool,
) -> str:
    formatted: list[str | tuple[str, str, str]] = []

    for index, arg in enumerate(arguments):
        if isinstance(arg, str):
            formatted.append(shlex.quote(arg))
            continue

        if not isinstance(arg, Secret):
            # this can only happen if plugin developers are ignoring the API's typing.
            raise _make_helpful_exception(index, arguments)

        secret = arg
        secret_name = surrogated_secrets[secret.id]

        if secret.pass_safely:
            formatted.append(shlex.quote(f"{secret_name}:{password_store_file}"))
            continue

        # we are meant to pass it as plain secret here, but we
        # maintain a list of plugins that have a very special hack in place.

        if apply_password_store_hack:
            # fall back to old hack, for now
            formatted.append(("store", secret_name, arg.format))
            continue

        # TODO: I think we can check this much earlier now.
        try:
            secret_value = passwords[secret_name]
        except KeyError:
            config_warnings.warn(
                f'The stored password "{secret_name}" used by host "{host_name}"' " does not exist."
            )
            secret_value = "%%%"
        formatted.append(shlex.quote(secret.format % secret_value))

    return " ".join(
        password_store.hack.apply_password_hack(
            formatted,
            passwords,
            password_store_file,
            config_warnings.warn,
            _make_log_label(host_name),
        ),
    )


def _make_log_label(host_name: str | None, description: ServiceName | None = None) -> str:
    if host_name and description:
        return f' used by service "{description}" on host "{host_name}"'
    if host_name:
        return f' used by host "{host_name}"'
    return ""


def _make_helpful_exception(index: int, arguments: Sequence[str | Secret]) -> TypeError:
    """Create a developer-friendly exception for invalid arguments"""
    raise TypeError(
        f"Got invalid argument list from SSC plugin: {arguments[index]!r} at index {index} in {arguments!r}. "
        "Expected either `str` or `Secret`."
    )


def replace_macros(string: str, macros: Mapping[str, str]) -> str:
    for macro, replacement in macros.items():
        string = string.replace(macro, str(replacement))
    return string
