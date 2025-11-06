#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa A002  # we're shadowing `help` to be consistent with the argparse API

import argparse

from ._impl import dereference_secret, Secret


def parser_add_secret_option(
    parser: argparse.ArgumentParser,
    /,
    *,
    short: str | None = None,
    long: str,
    help: str,
    required: bool,
) -> None:
    """Add mutually exclusive secret options to an argument parser.

    Creates two mutually exclusive options for handling secrets:
     * A direct secret option using the provided long an short names.
       This is intended for debuggnig purposes, but keep in mind that
       using it will expose the actual secret in the commandline.
     * An option to provide the password store reference using the long
       name with "-id" suffix: '<long>-id'. This should be used in the
       commandline that is created by the server side calls plugin.
       This prevents the actual secret from showing on the commandline or
       in the fetcher configuration.

    Args:
        parser: The argument parser to add options to
        short: Optional short option name (e.g., "-s") for convenience.
            It will only be used for the direct option. Must start with
            exactly one "-".
        long: Long option name (must start with "--", e.g., "--password")
        help: Help text for the direct secret option
        required: Whether one of the two options must be provided

    Raises:
        ValueError: If long option doesn't start with "--"

    Example:
        To create the options: --password, -p, --password-id

        >>> OPTION_NAME = "password"  # reuse this for `resolve_secret_option`
        >>> parser = argparse.ArgumentParser()
        >>> parser_add_secret_option(
        ...     parser,
        ...     short="-p",
        ...     long=f"--{OPTION_NAME}",
        ...     help="Database password",
        ...     required=True
        ... )
    """
    # Some custom validation, because the exception raised by argparse is rather obscure.
    if short and len(short) - len(short.lstrip("-")) != 1:
        raise ValueError('short option must start with exactly one "-"')
    if not long.startswith("--"):
        raise ValueError('long option must start with "--"')

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
    """Resolves a secret option from the argument parser namespace.

    Depending what "long" option you used in `parser_add_secret_option`, this function
    will either dereference the secret given by "--<LONG>-id" or use the explicit secret
    given by "--<LONG>".

    Args:
        args: The parsed arguments namespace as created by an argparse parser that used
            :func:`parser_add_secret_option`.
        option_name: The name of the option as passed to :func:`parser_add_secret_option`,
            without the leading dashes.

    Raises:
        TypeError: If neither of the two options where specified.

    """
    if (secret_id := getattr(args, f"{option_name}_id", None)) is not None:
        return dereference_secret(secret_id)

    if isinstance(secret := getattr(args, option_name, None), Secret):
        return secret

    raise TypeError(f"{option_name} is not of type Secret: {secret}")
