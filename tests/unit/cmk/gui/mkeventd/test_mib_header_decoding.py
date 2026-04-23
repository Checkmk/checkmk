#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.gui.mkeventd.wato import ModeEventConsoleMIBs


def test_parse_snmp_mib_header_handles_non_utf8_bytes(tmp_path: Path) -> None:
    mib = tmp_path / "BAD-MIB.txt"
    # 0x92 is a common Windows-1252 "right single quote" that is not valid UTF-8.
    mib.write_bytes(
        b"BAD-MIB DEFINITIONS ::= BEGIN\n"
        b'ORGANIZATION "Some \x92vendor\x92 name"\n'
        b"-- a comment\n"
        b"someObject OBJECT IDENTIFIER ::= { enterprises 1 }\n"
        b"END\n"
    )

    info = ModeEventConsoleMIBs._parse_snmp_mib_header(None, mib)  # type: ignore[arg-type]

    assert info.name == "BAD-MIB"
