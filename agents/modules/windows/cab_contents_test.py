#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test for unwanted files in the python.cab"""

import os
from pathlib import Path

import pytest
from cabarchive import CabArchive  # type: ignore[import-not-found]

_DENIED_BINARIES = {
    "sqlite3.dll",
    "_sqlite3.pyd",
}
_EXPECTED_PRESENT = {
    "python.exe",
    "libcrypto-3.dll",
}


@pytest.fixture(scope="module", name="cab_archive")
def _cab_archive() -> CabArchive:
    return CabArchive(Path(os.environ["PYTHON_CAB"]).read_bytes())


def test_cab_contents(cab_archive: CabArchive) -> None:
    basenames = {m.rsplit("\\", 1)[-1].lower() for m in cab_archive}

    missing = _EXPECTED_PRESENT - basenames
    assert not missing, f"We are missing {','.join(missing)} from the cab"
    disallowed = _DENIED_BINARIES & basenames
    assert not disallowed, f"We have disallowed binaries {','.join(disallowed)} in the cab"


def test_base_python_has_no_site_packages(cab_archive: CabArchive) -> None:
    # The agent runs the venv, which does not see the base interpreter's
    # site-packages: anything there would only ship as an unused second copy.
    members = {m.replace("\\", "/").lstrip("/") for m in cab_archive}

    base_site_packages = {m for m in members if m.lower().startswith("lib/site-packages/")} - {
        "Lib/site-packages/README.txt"
    }

    assert not base_site_packages, f"The base python has {sorted(base_site_packages)[:5]}"
