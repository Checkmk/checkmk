#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.collection.agent_based.skyhigh_webgateway_cpu_load import (
    snmp_section_skyhigh_webgateway_cpu_load,
)
from cmk.plugins.lib.cpu import Load, Section


def test_skyhigh_section_produces_cpu_section() -> None:
    assert snmp_section_skyhigh_webgateway_cpu_load.name == "skyhigh_webgateway_cpu_load"
    assert snmp_section_skyhigh_webgateway_cpu_load.parsed_section_name == "cpu"


@pytest.mark.parametrize(
    ["string_table", "expected_section"],
    [
        pytest.param(
            [
                [["100", "1.00"], ["200", "2.00"], ["300", "3.00"]],
                [[".0.0"], [".0.0"]],
            ],
            Section(
                load=Load(load1=1.00, load5=2.00, load15=3.00),
                num_cpus=2,
            ),
            id="typical skyhigh data with 2 cpus",
        ),
        pytest.param(
            [
                [["50", "0.50"], ["75", "0.75"], ["120", "1.20"]],
                [],
            ],
            Section(
                load=Load(load1=0.50, load5=0.75, load15=1.20),
                num_cpus=1,
            ),
            id="no cpu count from hrProcessorFrwID falls back to 1",
        ),
        pytest.param(
            [
                [["", "0.10"], ["", "0.20"], ["", "0.30"]],
                [[".0.0"], [".0.0"], [".0.0"], [".0.0"]],
            ],
            Section(
                load=Load(load1=0.10, load5=0.20, load15=0.30),
                num_cpus=4,
            ),
            id="only float values present",
        ),
        pytest.param(
            [
                [["100", ""], ["200", ""], ["300", ""]],
                [[".0.0"]],
            ],
            Section(
                load=Load(load1=1.0, load5=2.0, load15=3.0),
                num_cpus=1,
            ),
            id="only integer values present",
        ),
        pytest.param(
            [
                [["100", "1.00"], ["200", "2.00"]],
                [[".0.0"]],
            ],
            None,
            id="incomplete load data returns None",
        ),
    ],
)
def test_parse_skyhigh_cpu_load(
    string_table: Sequence[StringTable], expected_section: Section | None
) -> None:
    assert snmp_section_skyhigh_webgateway_cpu_load.parse_function(string_table) == expected_section
