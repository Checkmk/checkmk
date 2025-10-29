#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa A002  # we're shadowing `help` to be consistent with the argparse API

import argparse

from ._impl import dereference_secret, Secret


def parser_add_secret_option(
    parser: argparse.ArgumentParser,
    short: str | None,
    long: str,
    help: str,
    required: bool = True,
) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument(
        *((short,) if short else ()),
        long,
        default=None,
        help=help,
        type=Secret,
    )
    group.add_argument(
        f"{long}-id",
        default=None,
        help=f'Same as "{long}", but containing the reference to the password store rather than the actual secret.',
    )


def resolve_secret_option(args: argparse.Namespace, option_name: str) -> Secret[str]:
    if (secret_id := getattr(args, f"{option_name}_id", None)) is not None:
        return dereference_secret(secret_id)

    if isinstance(secret := getattr(args, option_name, None), Secret):
        return secret

    raise TypeError(f"{option_name} is not of type Secret: {secret}")
