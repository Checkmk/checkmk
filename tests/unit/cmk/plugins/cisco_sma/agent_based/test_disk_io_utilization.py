#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import StringTable
from cmk.plugins.cisco_sma.agent_based.disk_io_utilization import parse


def test_parse_for_empty_string_table() -> None:
    assert parse(StringTable([])) is None


def test_parse_for_single_value() -> None:
    assert parse(StringTable([["42"]])) == 42.0
