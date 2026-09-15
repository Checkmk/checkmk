#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import runpy
import shutil
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "compile_mibs.py"

TEST_MIB = """\
CHECKMK-TEST-MIB DEFINITIONS ::= BEGIN

IMPORTS
    MODULE-IDENTITY, OBJECT-TYPE, Integer32, enterprises
        FROM SNMPv2-SMI;

checkmkTest MODULE-IDENTITY
    LAST-UPDATED "202601010000Z"
    ORGANIZATION "Checkmk GmbH"
    CONTACT-INFO "test"
    DESCRIPTION "A minimal MIB for testing the compiler wrapper"
    ::= { enterprises 99999 }

checkmkTestValue OBJECT-TYPE
    SYNTAX      Integer32
    MAX-ACCESS  read-only
    STATUS      current
    DESCRIPTION "A single value"
    ::= { checkmkTest 1 }

END
"""


def _provide_base_mibs(directory: Path) -> None:
    """The compiler resolves imports from the directories of the given MIBs, so the SMI base
    modules shipped with net-snmp are placed next to the MIB under test."""
    net_snmp_mibs = next(
        Path(os.environ["TEST_SRCDIR"]).glob("*net-snmp*/mibs/SNMPv2-SMI.txt")
    ).parent
    for name in ("SNMPv2-SMI", "SNMPv2-TC", "SNMPv2-CONF"):
        shutil.copy(net_snmp_mibs / f"{name}.txt", directory)


def _compile(destination: Path, sources: list[Path], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), str(destination), *map(str, sources)])
    runpy.run_path(str(SCRIPT), run_name="__main__")


def test_mib_is_compiled_into_python_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mib = tmp_path / "CHECKMK-TEST-MIB.txt"
    mib.write_text(TEST_MIB)
    _provide_base_mibs(tmp_path)
    destination = tmp_path / "compiled"

    _compile(destination, [mib], monkeypatch)

    compiled = (destination / "CHECKMK-TEST-MIB.py").read_text()
    assert "checkmkTestValue" in compiled


def test_broken_mib_fails_the_compilation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mib = tmp_path / "BROKEN-MIB.txt"
    mib.write_text("BROKEN-MIB DEFINITIONS ::= BEGIN\nthis is not ASN.1\nEND\n")

    with pytest.raises(Exception, match="Could not compile mib BROKEN-MIB"):
        _compile(tmp_path / "compiled", [mib], monkeypatch)
