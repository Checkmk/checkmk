#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.collection.agent_based.ucd_cpu_load import parse_ucd_cpu_load
from cmk.plugins.lib.cpu import Load, Section


@pytest.mark.parametrize(
    ["string_table", "expected_section"],
    [
        pytest.param(
            [
                [["312", "3.123213"], ["280", "2.78897"], ["145", "1.34563546"]],
                [[".0.0"], [".0.0"], [".0.0"], [".0.0"]],
            ],
            Section(
                load=Load(load1=3.123213, load5=2.78897, load15=1.34563546),
                num_cpus=4,
            ),
            id="complete dataset",
        ),
        pytest.param(
            [[["", "5,234"], ["234", ""], ["", ""]], []],
            Section(
                load=Load(load1=5.234, load5=2.34, load15=0),
                num_cpus=1,
            ),
            id="data missing",
        ),
    ],
)
def test_parse_ucd_cpu_load(string_table: Sequence[StringTable], expected_section: Section) -> None:
    assert parse_ucd_cpu_load(string_table) == expected_section
