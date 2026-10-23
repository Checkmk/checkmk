#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ec.mib_compiler import compile_mib

_SELF_CONTAINED_MIB = """TEST-MIB DEFINITIONS ::= BEGIN
testRoot OBJECT IDENTIFIER ::= { iso 3 6 1 4 1 99999 }
END
"""


def test_valid_mib_is_written_to_destination(tmp_path: Path) -> None:
    results = compile_mib(
        mibname="TEST-MIB",
        content=_SELF_CONTAINED_MIB,
        source_dirs=[],
        search_dirs=[],
        destination_dir=tmp_path,
    )

    assert results["TEST-MIB"] == "compiled"
    assert (tmp_path / "TEST-MIB.py").exists()


def test_invalid_mib_is_reported_as_failed(tmp_path: Path) -> None:
    results = compile_mib(
        mibname="BROKEN-MIB",
        content="BROKEN-MIB DEFINITIONS ::= BEGIN nonsense",
        source_dirs=[],
        search_dirs=[],
        destination_dir=tmp_path,
    )

    assert results["BROKEN-MIB"] == "failed"
