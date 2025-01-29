#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.collection.agent_based.hpux_cpu import parse_hpux_cpu
from cmk.plugins.lib.cpu import Load, Section


@pytest.mark.parametrize(
    ["string_table", "expected_section"],
    [
        pytest.param(
            [
                [
                    "10:45am",
                    "up",
                    "161",
                    "days,",
                    "18:58,",
                    "6",
                    "users,",
                    "load",
                    "average:",
                    "0.08,",
                    "0.07,",
                    "0.06",
                ],
                [
                    "32",
                    "logical",
                    "processors",
                    "(4",
                    "per",
                    "socket)",
                ],
            ],
            Section(
                load=Load(load1=0.08, load5=0.07, load15=0.06),
                num_cpus=32,
            ),
            id="with number of cpus",
        ),
        pytest.param(
            [
                [
                    "10:44am",
                    "up",
                    "239",
                    "days,",
                    "19:28,",
                    "6",
                    "users,",
                    "load",
                    "average:",
                    "0.05,",
                    "0.10,",
                    "0.13",
                ]
            ],
            Section(
                load=Load(load1=0.05, load5=0.10, load15=0.13),
                num_cpus=1,
            ),
            id="without number of cpus",
        ),
        pytest.param(
            [
                [
                    "10:44am",
                    "up",
                    "239",
                    "days,",
                    "19:28,",
                    "6",
                    "users,",
                ]
            ],
            None,
            id="no load information",
        ),
        pytest.param(
            [],
            None,
            id="empty section",
        ),
    ],
)
def test_parse_hpux_cpu(
    string_table: StringTable,
    expected_section: Section | None,
) -> None:
    assert parse_hpux_cpu(string_table) == expected_section
