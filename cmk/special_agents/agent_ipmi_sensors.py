#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for collecting data from IPMI sensors via freeipmi or ipmitool.
"""

import os
import subprocess
import sys
from argparse import _SubParsersAction
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Literal

from cmk.special_agents.v0_unstable.agent_common import special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser


@dataclass(frozen=True)
class Query:
    section_name: Literal["ipmi", "ipmi_discrete", "ipmi_sensors"]
    types: tuple[str, ...]
    excludes: tuple[str, ...]


QUERIES_IPMITOOL: Iterable[Query] = (
    Query("ipmi", types=("sensor", "list"), excludes=("command failed", "discrete")),
    Query("ipmi_discrete", types=("sdr", "elist", "compact"), excludes=()),
)


QUERIES_FREEIPMI: Iterable[Query] = (Query("ipmi_sensors", types=(), excludes=()),)


def _add_freeipmi_args(subparsers: _SubParsersAction) -> None:
    parser_freeipmi = subparsers.add_parser(
        "freeipmi",
        help="Use freeipmi",
    )
    parser_freeipmi.add_argument(
        "privilege_lvl",
        type=str,
        metavar="PRIVILEGE-LEVEL",
        help="Privilege level",
        choices=("user", "operator", "admin"),
    )
    parser_freeipmi.add_argument(
        "--driver",
        type=str,
        metavar="DRIVER",
        help="IPMI driver",
    )
    parser_freeipmi.add_argument(
        "--driver_type",
        type=str,
        metavar="DRIVER-TYPE",
        help="Driver type to use instead of doing an auto selection",
    )
    parser_freeipmi.add_argument(
        "--key",
        type=str,
        metavar="KEY",
        help="K_g BMC key to use when authenticating with the remote host for IPMI 2.0",
    )
    parser_freeipmi.add_argument(
        "--quiet_cache",
        action="store_true",
        help="Do not output information about cache creation/deletion",
    )
    parser_freeipmi.add_argument(
        "--sdr_cache_recreate",
        action="store_true",
        help="Automatically recreate the sensor data repository (SDR) cache",
    )
    parser_freeipmi.add_argument(
        "--interpret_oem_data",
        action="store_true",
        help="Attempt to interpret OEM data",
    )
    parser_freeipmi.add_argument(
        "--output_sensor_state",
        action="store_true",
        help="Output sensor state",
    )
    parser_freeipmi.add_argument(
        "--ignore_not_available_sensors",
        action="store_true",
        help="Ignore not-available (i.e. N/A) sensors in output",
    )
    parser_freeipmi.add_argument(
        "--output_sensor_thresholds",
        action="store_true",
        help="Output sensor thresholds",
    )


def _add_ipmitool_args(subparsers: _SubParsersAction) -> None:
    parser_ipmitool = subparsers.add_parser(
        "ipmitool",
        help="Use ipmitool",
    )
    parser_ipmitool.add_argument(
        "privilege_lvl",
        type=str,
        metavar="PRIVILEGE-LEVEL",
        help="Privilege level",
        choices=("callback", "user", "operator", "administrator"),
    )
    parser_ipmitool.add_argument(
        "--intf",
        type=str,
        choices=("open", "imb", "lan", "lanplus"),
        metavar="INTERFACE",
        help=(
            "IPMI Interface to be used. If not specified, the default interface as set at compile "
            "time will be used."
        ),
    )


def _parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument(
        "host",
        type=str,
        metavar="HOST",
        help="Host name or IP address",
    )
    parser.add_argument(
        "user",
        type=str,
        metavar="USER",
        help="Username",
    )
    parser.add_argument(
        "password",
        type=str,
        metavar="PASSWORD",
        help="Password",
    )
    ipmi_cmd_subparsers = parser.add_subparsers(
        required=True,
        dest="ipmi_cmd",
        metavar="IPMI-CMD",
        help="IPMI command to be used. Possible values are 'freeipmi' or 'ipmitool'.",
    )
    _add_freeipmi_args(ipmi_cmd_subparsers)
    _add_ipmitool_args(ipmi_cmd_subparsers)
    return parser.parse_args(argv)


def _freeipmi_additional_args(
    args: Args,
) -> Iterable[str]:
    yield from chain.from_iterable(
        (freeipmi_opt, value)
        for argname, freeipmi_opt in [
            ("driver", "-D"),
            ("driver_type", "--driver-type"),
            ("key", "-k"),
        ]
        if (
            value := getattr(
                args,
                argname,
            )
        )
    )
    yield from (
        f"--{bool_arg.replace('_', '-')}"
        for bool_arg in [
            "quiet_cache",
            "sdr_cache_recreate",
            "interpret_oem_data",
            "output_sensor_state",
            "ignore_not_available_sensors",
            "output_sensor_thresholds",
        ]
        if getattr(
            args,
            bool_arg,
        )
    )


def _prepare_freeipmi_call(
    args: Args,
) -> Sequence[str]:
    return [
        "ipmi-sensors",
        "-h",
        args.host,
        "-u",
        args.user,
        "-p",
        args.password,
        "-l",
        args.privilege_lvl,
        *_freeipmi_additional_args(args),
    ]


def _ipmitool_additional_args(
    args: Args,
) -> Iterable[str]:
    if iface := getattr(args, "intf"):
        yield "-I"
        yield iface


def _prepare_ipmitool_call(
    args: Args,
) -> Sequence[str]:
    return [
        "ipmitool",
        "-H",
        args.host,
        "-U",
        args.user,
        "-P",
        args.password,
        "-L",
        args.privilege_lvl,
        *_ipmitool_additional_args(args),
    ]


def _filter_output(
    data: str,
    excludes: Iterable[str],
) -> Iterable[str]:
    return [
        f"{line}\n"
        for line in data.splitlines()
        if not line.startswith("ID") and not any(e in line for e in excludes)
    ]


def _main(args: Args) -> int:
    os.environ["PATH"] = "/usr/local/sbin:/usr/sbin:/sbin:" + os.environ["PATH"]

    match args.ipmi_cmd:
        case "freeipmi":
            ipmi_call = _prepare_freeipmi_call(args)
            queries = QUERIES_FREEIPMI
        case "ipmitool":
            ipmi_call = _prepare_ipmitool_call(args)
            queries = QUERIES_IPMITOOL
        case unknown:
            raise NotImplementedError(f"No such command: {unknown}")

    if args.debug:
        sys.stderr.write("Executing: '%s'\n" % subprocess.list2cmdline(ipmi_call))

    errors = []
    for query in queries:
        sys.stdout.write(f"<<<{query.section_name}:sep(124)>>>\n")
        try:
            try:
                completed_process = subprocess.run(
                    [
                        *ipmi_call,
                        *query.types,
                    ],
                    close_fds=True,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    encoding="utf-8",
                    check=False,
                )
            except FileNotFoundError as e:
                raise Exception(
                    "Could not find '{}' command (PATH: {})".format(
                        args.ipmi_cmd, os.environ.get("PATH")
                    )
                ) from e

            if completed_process.stderr:
                errors.append(completed_process.stderr)

            sys.stdout.writelines(_filter_output(completed_process.stdout, query.excludes))

        except Exception as e:
            errors.append(str(e))

    if errors:
        sys.stderr.write("ERROR: '%s'.\n" % ", ".join(errors))
        return 1
    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(_parse_arguments, _main)
