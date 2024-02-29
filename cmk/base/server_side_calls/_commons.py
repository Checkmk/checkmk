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
    passwords_from_store: Mapping[str, str],
) -> str:
    """Prepares a check command for execution by Checkmk

    In case a list is given it quotes element if necessary. It also prepares password store entries
    for the command line. These entries will be completed by the executed program later to get the
    password from the password store.
    """
    passwords: list[tuple[str, str, str]] = []
    formatted: list[str] = []
    for arg in command_spec:
        if isinstance(arg, (int, float)):
            formatted.append(str(arg))

        elif isinstance(arg, str):
            formatted.append(shlex.quote(arg))

        elif isinstance(arg, tuple) and len(arg) == 3:
            pw_ident, preformated_arg = arg[1:]
            try:
                password = passwords_from_store[pw_ident]
            except KeyError:
                if hostname and description:
                    descr = f' used by service "{description}" on host "{hostname}"'
                elif hostname:
                    descr = f' used by host host "{hostname}"'
                else:
                    descr = ""

                config_warnings.warn(
                    f'The stored password "{pw_ident}"{descr} does not exist (anymore).'
                )
                password = "%%%"

            pw_start_index = str(preformated_arg.index("%s"))
            formatted.append(shlex.quote(preformated_arg % ("*" * len(password))))
            passwords.append((str(len(formatted)), pw_start_index, pw_ident))

        else:
            raise ActiveCheckError(f"Invalid argument for command line: {arg!r}")

    if passwords:
        pw = ",".join(["@".join(p) for p in passwords])
        pw_store_arg = f"--pwstore={pw}"
        formatted = [shlex.quote(pw_store_arg)] + formatted

    return " ".join(formatted)


def replace_passwords(
    host_name: str,
    stored_passwords: Mapping[str, str],
    arguments: Sequence[str | Secret],
    surrogated_secrets: Mapping[int, tuple[Literal["store", "password"], str]],
) -> str:
    passwords: list[tuple[str, str, str]] = []
    formatted: list[str] = []

    for arg in arguments:
        if isinstance(arg, str):
            formatted.append(shlex.quote(arg))
            continue

        secret_type, secret_value = surrogated_secrets[arg.id]

        match secret_type:
            case "password":
                formatted.append(shlex.quote(arg.format % secret_value))
            case "store":
                try:
                    password = stored_passwords[secret_value]
                except KeyError:
                    config_warnings.warn(
                        f'The stored password "{secret_value}" used by host "{host_name}"'
                        " does not exist."
                    )
                    password = "%%%"

                pw_start_index = str(arg.format.index("%s"))
                formatted.append(shlex.quote(arg.format % ("*" * len(password))))
                passwords.append((str(len(formatted)), pw_start_index, secret_value))

    if passwords:
        pw = ",".join(["@".join(p) for p in passwords])
        pw_store_arg = f"--pwstore={pw}"
        formatted = [shlex.quote(pw_store_arg)] + formatted

    return " ".join(formatted)


def replace_macros(string: str, macros: Mapping[str, str]) -> str:
    for macro, replacement in macros.items():
        string = string.replace(macro, str(replacement))
    return string
