#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test for unwanted files in the python.cab"""

import os
import re
from pathlib import Path

_DENIED_BINARIES = {
    "sqlite3.dll",
    "_sqlite3.pyd",
}
_EXPECTED_PRESENT = {
    "python.exe",
    "libcrypto-3.dll",
}
# The agent runs the venv, which does not see the base interpreter's
# site-packages: anything there, pip or leaked build tools, would only ship as
# an unused copy.
_ALLOWED_IN_BASE_SITE_PACKAGES = re.compile(r"^README\.txt$", re.IGNORECASE)


def test_cab_contents(python_to_test: Path) -> None:
    for python_name in os.listdir(python_to_test):
        basenames = {
            p.name.lower() for p in (python_to_test / python_name).rglob("*") if p.is_file()
        }

        missing = _EXPECTED_PRESENT - basenames
        assert not missing, f"We are missing {','.join(missing)} from {python_name}"
        disallowed = _DENIED_BINARIES & basenames
        assert (
            not disallowed
        ), f"We have disallowed binaries {','.join(disallowed)} in {python_name}"


def test_base_site_packages_hold_no_build_tools(python_to_test: Path) -> None:
    for python_name in os.listdir(python_to_test):
        site_packages = python_to_test / python_name / "Lib" / "site-packages"
        # A cabinet keeps no empty directories.
        present = site_packages.iterdir() if site_packages.is_dir() else iter(())

        unexpected = sorted(
            p.name for p in present if not _ALLOWED_IN_BASE_SITE_PACKAGES.match(p.name)
        )

        assert not unexpected, f"{python_name} ships {', '.join(unexpected)} in Lib/site-packages"
