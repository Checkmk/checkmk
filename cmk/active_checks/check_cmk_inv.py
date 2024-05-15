#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import subprocess
import sys
from collections.abc import Sequence


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check_cmk_inv",
        description="""Check Checkmk inventory""",
    )

    parser.add_argument(
        "hostname",
        type=str,
        metavar="HOSTNAME",
        help="Host for which the inventory is executed",
    )

    parser.add_argument(
        "--inv-fail-status",
        type=int,
        default=1,
        help="State when inventory fails",
    )

    parser.add_argument(
        "--hw-changes",
        type=int,
        default=0,
        help="State when hardware changes are detected",
    )

    parser.add_argument(
        "--sw-changes",
        type=int,
        default=0,
        help="State when software packages info is missing",
    )

    parser.add_argument(
        "--sw-missing",
        type=int,
        default=0,
        help="State when software packages info is missing",
    )

    return parser.parse_args(argv)


def get_command(args: argparse.Namespace) -> Sequence[str]:
    return [
        "cmk",
        f"--inv-fail-status={args.inv_fail_status}",
        f"--hw-changes={args.hw_changes}",
        f"--sw-changes={args.sw_changes}",
        f"--sw-missing={args.sw_missing}",
        "--inventory-as-check",
        args.hostname,
    ]


def main(
    argv: Sequence[str] | None = None,
) -> int:
    args = parse_arguments(argv or sys.argv[1:])
    cmd = get_command(args)

    completed_process = subprocess.run(cmd, capture_output=True, encoding="utf8", check=False)

    if completed_process.stderr:
        print(completed_process.stderr, file=sys.stderr)

    if completed_process.stdout:
        print(completed_process.stdout)

    return completed_process.returncode
