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
def _cab_archive() -> CabArchive:  # type: ignore[misc]
    return CabArchive(Path(os.environ["PYTHON_CAB"]).read_bytes())


def test_cab_contents(cab_archive: CabArchive) -> None:
    basenames = {m.rsplit("\\", 1)[-1].lower() for m in cab_archive}

    missing = _EXPECTED_PRESENT - basenames
    assert not missing, f"We are missing {','.join(missing)} from the cab"
    disallowed = _DENIED_BINARIES & basenames
    assert not disallowed, f"We have disallowed binaries {','.join(disallowed)} in the cab"
