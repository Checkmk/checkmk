#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.collection.agent_based.rmon_stats import parse_rmon_stats


def test_parse_rmon_stats_handles_empty_counter() -> None:
    string_table = [
        [
            "1",
            "100 Packets",
            "200 Packets",
            "300 Packets",
            "400 Packets",
            "",
            "500 Packets",
            "600 Packets",
            "700 Packets",
        ],
    ]
    result = parse_rmon_stats(string_table)
    assert result["1"]["128-255b"] == 0
    assert result["1"]["bcast"] == 100
