#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This consolidates the hack that we currently use to make plugins
password store compatible.

We are working towards a more staight forward solution.
"""

import shlex
import sys
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import NoReturn

HACK_AGENTS = {
    # For the plugins developed against the cmk.server_side_calls.v1 we
    # need to know whether they support the password store natively, or
    # if we have to apply the password store hack.
    # Make sure to have *all* special agent plugins listed here, so we
    # can test for it
    "azure_status": False,  # needs no secret
    "bazel_cache": True,
    "bi": False,  # needs no secret
    "cisco_meraki": True,
    "cisco_prime": True,
    "elasticsearch": True,
    "gcp": True,
    "jenkins": True,
    "mobileiron": True,
    "netapp_ontap": True,
    "prism": True,
    "proxmox_ve": True,
    "pure_storage_fa": True,
    "three_par": True,
    "prometheus": False,
}


HACK_CHECKS = {
    # For the plugins developed against the cmk.server_side_calls.v1 we
    # need to know whether they support the password store natively, or
    # if we have to apply the password store hack.
    # Make sure to have *all* active check plug-ins listed here, so we
    # can test for it
    "by_ssh": False,  # has no secret
    "cert": False,  # has no secret
    "cmk_inv": False,  # has no secret
    "dns": False,  # has no secret
    "elasticsearch_query": True,
    "form_submit": False,  # has no secret
    "ftp": False,  # has no secret
    "httpv2": False,  # yay!
    "icmp": False,  # has no secret
    "mkevents": False,  # has no secret
    "notify_count": False,  # has no secret
    "sql": True,
    "ssh": False,  # has no secret
    "traceroute": False,  # has no secret
}


def _bail_out(s: str) -> NoReturn:
    sys.stdout.write("UNKNOWN - %s\n" % s)
    sys.stderr.write("UNKNOWN - %s\n" % s)
    sys.exit(3)


def resolve_password_hack(
    input_argv: Iterable[str], password_lookup: Callable[[Path, str], str]
) -> list[str]:
    argv = list(input_argv)

    if len(argv) < 2:
        return argv  # command line too short

    if not [a for a in argv if a.startswith("--pwstore")]:
        return argv  # no password store in use

    # --pwstore=4@4@file@web,6@0@file@foo
    #  In the 4th argument at char 4 replace the following bytes
    #  with the passwords stored in 'file' under the ID 'web'
    #  In the 6th argument at char 0 insert the password from 'file' with the ID 'foo'

    # Extract first argument and parse it

    pwstore_args = argv.pop(1).split("=", 1)[1]

    for password_spec in pwstore_args.split(","):
        parts = password_spec.split("@")
        if len(parts) != 4:
            _bail_out(f"pwstore: Invalid --pwstore entry: {password_spec}")

        try:
            num_arg, pos_in_arg, pw_file, pw_id = (
                int(parts[0]),
                int(parts[1]),
                Path(parts[2]),
                parts[3],
            )
        except ValueError:
            _bail_out(f"pwstore: Invalid --pwstore entry: {password_spec}")

        try:
            arg = argv[num_arg]
        except IndexError:
            _bail_out("pwstore: Argument %d does not exist" % num_arg)

        try:
            password = password_lookup(pw_file, pw_id)
        except ValueError as exc:
            _bail_out(f"pwstore: {exc}")

        argv[num_arg] = arg[:pos_in_arg] + password + arg[pos_in_arg + len(password) :]

    return argv


def apply_password_hack(
    command_spec: Iterable[str | tuple[str, str, str]],
    passwords: Mapping[str, str],
    pw_file: Path,
    logger: Callable[[str], None],
    log_label: str,
) -> list[str]:
    """Prepares a check command of a tool that uses resolve_password_hacks"""
    replacements: list[tuple[str, str, str]] = []
    formatted: list[str] = []
    for arg in command_spec:
        if isinstance(arg, str):
            formatted.append(arg)
            continue

        if isinstance(arg, tuple) and len(arg) == 3:
            pw_ident, preformated_arg = arg[1:]
        else:
            raise ValueError(f"Invalid argument for command line: {arg!r}")

        try:
            password = passwords[pw_ident]
        except KeyError:
            logger(f'The stored password "{pw_ident}"{log_label} does not exist (anymore).')
            password = "%%%"

        pw_start_index = str(preformated_arg.index("%s"))
        formatted.append(shlex.quote(preformated_arg % ("*" * len(password))))
        replacements.append((str(len(formatted)), pw_start_index, pw_ident))

    if replacements:
        pw = ",".join(
            (
                f"{num_arg}@{pos_in_arg}@{pw_file}@{pw_id}"
                for num_arg, pos_in_arg, pw_id in replacements
            )
        )
        pw_store_arg = f"--pwstore={pw}"
        formatted = [shlex.quote(pw_store_arg)] + formatted

    return formatted
