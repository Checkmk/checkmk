#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import Path

from cmk.utils.password_store.hack import apply_password_hack, resolve_password_hack

APPLIED = [
    "--pwstore=3@13@/some/path/to/store@one,4@15@/some/path/to/store@two",
    "--normal",
    "--also-normal",
    "'--password=!!*****!!'",
    "'--credential=..********..'",
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

    assert (
        apply_password_hack(
            command_spec,
            PASSWORDS,
            Path("/some/path/to/store"),
            lambda x: None,
            "log_label_smth",
        )
        == APPLIED
    )


def test_password_hack_resolve() -> None:
    assert resolve_password_hack(
        [
            "__ignored__",
            *[a.strip("'") for a in APPLIED],  # remove quoting is normally done by bash
        ],
        lambda _path_ignored, x: PASSWORDS[x],
    ) == [
        "__ignored__",
        "--normal",
        "--also-normal",
        "--password=!!12345!!",
        "--credential=..ääääääää..",
        "--end",
    ]
