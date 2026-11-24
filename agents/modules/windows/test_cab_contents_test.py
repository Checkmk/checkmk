#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The test Python cab has what the pytest suites import on Windows."""

import os
from pathlib import Path

import pytest
from cab_members import members as cab_members
from cab_members import unwanted


@pytest.fixture(scope="module", name="members")
def _members() -> set[str]:
    return cab_members(Path(os.environ["PYTHON_TEST_CAB"]))


@pytest.mark.parametrize(
    "member",
    [
        "python.exe",
        # python-3.cab strips unittest; pytest imports it at startup.
        "lib/unittest/__init__.py",
        "lib/site-packages/pytest/__init__.py",
        "lib/site-packages/yaml/__init__.py",
        "lib/site-packages/pywin32.pth",
        "lib/site-packages/win32/win32evtlog.pyd",
    ],
)
def test_member_present(members: set[str], member: str) -> None:
    assert member in members, f"{member} missing from the test Python cab"


def test_no_venv(members: set[str]) -> None:
    assert not {m for m in members if m.startswith(".venv/")}


def test_leaves_out_what_no_cab_ships(members: set[str]) -> None:
    shipped = unwanted(members)

    assert not shipped, f"The test cab ships {sorted(shipped)[:5]}"
