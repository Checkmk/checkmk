#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Service
from cmk.plugins.oracle.agent_based.oracle_logswitches import (
    discover_oracle_logswitches,
    parse_oracle_logswitches,
)


def test_discover_normal() -> None:
    assert list(discover_oracle_logswitches(parse_oracle_logswitches([["orcl", "42"]]))) == [
        Service(item="orcl")
    ]


def test_discover_skips_error_row() -> None:
    error_info = [["orcl", "ORA-16000: database open for read-only access"]]
    assert not list(discover_oracle_logswitches(parse_oracle_logswitches(error_info)))
