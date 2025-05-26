#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from getpass import getpass
from pathlib import Path

import cmk.ccc.version as cmk_version
from cmk.ccc.user import UserId

from cmk.utils.paths import htpasswd_file

from cmk.gui.utils.htpasswd import Htpasswd

from cmk.crypto import password_hashing
from cmk.crypto.password import Password

HTPASSWD_FILE = htpasswd_file


class InvalidUsernameError(ValueError):
    """Indicates that the provided username is not a valid UserId"""


class InvalidPasswordError(ValueError):
    """Indicates that the provided username is not a valid UserId"""


def _parse_args(args: Sequence[str]) -> argparse.Namespace:
    """Parse arguments from 'args', if given, otherwise from sys.argv"""
    parser = argparse.ArgumentParser(
        description="""
cmkpasswd is a utility to add and change Checkmk user accounts in a similar fashion to htpasswd.
cmkpasswd will select a secure hashing algorithm that is compatible with this version of Checkmk to protect passwords.
Note that the main purpose of this program is setting and resetting the password for the cmkadmin user.
For other tasks, such as deleting or deactivating users, use the web interface.
"""
    )
    parser.add_argument(
        "username",
        type=str,
        help="the username of the user whose password to add or change",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s shipped with Checkmk version {cmk_version.__version__}",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        default=False,
        help="don't write the result to the password file but print to standard output",
        dest="no_file",
    )
    parser.add_argument(
        "-i",
        "--stdin",
        action="store_true",
        default=False,
        help="read the password from standard input without verification (useful for script usage)",
        dest="no_prompt",
    )

    return parser.parse_args(args)


def _ask_password() -> Password:
    """Prompt the user to enter the password and re-type it for verification"""
    pw = Password(getpass("New password: "))
    if pw.raw != getpass("Re-type new password: "):
        raise ValueError("Password verification error")
    return pw


def _read_password() -> Password:
    """Read password from stdin without prompt and confirmation"""
    return Password(input())


def _run_cmkpasswd(
    username: str, get_password: Callable[[], Password], dst_file: Path | None
) -> None:
    try:
        user_id = UserId(username)
    except ValueError as e:
        raise InvalidUsernameError(e)

    try:
        password = get_password()
        pw_hash = password_hashing.hash_password(password)
    except (password_hashing.PasswordTooLongError, ValueError) as e:
        raise InvalidPasswordError(e)

    if dst_file is not None:
        Htpasswd(dst_file).save(user_id, pw_hash)
    else:
        sys.stdout.write(Htpasswd.serialize_entries([(user_id, pw_hash)]) + "\n")


def main(args: Sequence[str]) -> int:
    parsed_args = _parse_args(args)

    target_file = HTPASSWD_FILE if not parsed_args.no_file else None

    # this is a callable to delay prompting until after the username was parsed successfully
    get_password = _read_password if parsed_args.no_prompt else _ask_password

    try:
        _run_cmkpasswd(parsed_args.username, get_password, target_file)

    except (
        OSError,
        InvalidPasswordError,
        InvalidUsernameError,
    ) as e:
        sys.stderr.write(f"cmk-passwd: {e}\n")
        return 1

    return 0
