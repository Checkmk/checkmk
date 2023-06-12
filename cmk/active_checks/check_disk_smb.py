#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from collections.abc import Sequence


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check_disk_smb",
        description="""Check SMB Disk plugin for monitoring""",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        metavar="TIMEOUT",
        default=15,
        help="Seconds before connection times out (Default: 15)",
    )
    parser.add_argument(
        "share",
        type=str,
        metavar="SHARE",
        help="Share name to be tested",
    )
    parser.add_argument(
        "-W",
        "--workgroup",
        type=str,
        metavar="WORKGROUP",
        help="Workgroup or Domain used.",
    )
    parser.add_argument(
        "-H",
        "--hostname",
        type=str,
        metavar="HOSTNAME",
        help="NetBIOS name of the server",
    )
    parser.add_argument(
        "-P",
        "--port",
        type=int,
        metavar="PORT",
        help="Port to be used to connect to. Some Windows boxes use 139, others 445.",
    )
    parser.add_argument(
        "--levels",
        type=int,
        nargs=2,
        default=[85, 95],
        metavar=("WARNING", "CRITICAL"),
        help="""Percent of used space at which a warning and critical will be generated (Defaults: 85 and 95).
            Warning percentage should be less than critical.""",
    )
    parser.add_argument(
        "-u",
        "--user",
        type=str,
        default="guest",
        metavar="USER",
        help='Username to log in to server. (Defaults to "guest")',
    )
    parser.add_argument(
        "-p",
        "--password",
        type=str,
        default="",
        metavar="PASSWORD",
        help="Password to log in to server. (Defaults to an empty password)",
    )
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        metavar="IP ADDRESS",
        help="IP-address of HOST (only necessary if HOST is in another network)",
    )
    parser.add_argument(
        "-C",
        "--configfile",
        type=str,
        metavar="CONFIGFILE",
        help="Path to configfile which should be used by smbclient (Defaults to smb.conf of your smb installation)",
    )

    return parser.parse_args(argv)
