#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import sys
from collections.abc import Sequence

from cmk.utils.password_store import lookup, pending_password_store_path


def _parse_args(args: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""
Retrieve a password from the Checkmk password store.
"""
    )
    parser.add_argument(
        "--lookup",
        required=True,
        type=str,
        metavar="PW_ID",
        help="The ID of the password to retrieve from the password store",
    )
    return parser.parse_args(args)


def main(args: Sequence[str]) -> int:
    parsed_args = _parse_args(args)

    try:
        password = lookup(pending_password_store_path(), parsed_args.lookup)
    except ValueError as e:
        sys.stderr.write(f"cmk-passwordstore: {e}\n")
        return 1
    sys.stdout.write(password)
    return 0
