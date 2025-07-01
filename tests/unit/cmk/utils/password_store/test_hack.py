#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Iterable

from pytest_mock import MockerFixture

from cmk.utils.password_store import replace_passwords

from cmk.base.config import _prepare_check_command

APPLIED = [
    "--pwstore=3@13@one,4@15@two",
    "--normal",
    "--also-normal",
    "'--password=!!*****!!'",
    "'--credential=..****************..'",
    "--end",
]
PASSWORDS = {
    "one": "12345",
    "two": "ääääääää",
}


def test_password_hack_apply() -> None:
    command_spec: Iterable[str | tuple[str, str, str]] = [
        "--normal",
        "--also-normal",
        ("ignored", "one", "--password=!!%s!!"),
        ("ignored", "two", "--credential=..%s.."),
        "--end",
    ]

    assert _prepare_check_command(
        command_spec,
        "hostname",
        "description",
        PASSWORDS,
    ) == " ".join(APPLIED)


def test_password_hack_resolve(mocker: MockerFixture) -> None:
    mocker.patch("cmk.utils.password_store.load_for_helpers", return_value=PASSWORDS.copy())
    sys_argv = [
        "__ignored__",
        *[a.strip("'") for a in APPLIED],  # remove quoting is normally done by bash
    ]
    mocker.patch.object(sys, "argv", sys_argv)

    replace_passwords()

    assert sys_argv == [
        "__ignored__",
        "--normal",
        "--also-normal",
        "--password=!!12345!!",
        "--credential=..ääääääää..",
        "--end",
    ]
