#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.ucd_cpu_load import parse_ucd_cpu_load
from cmk.base.plugins.agent_based.utils.cpu import Load, Section


@pytest.mark.parametrize(
    ["string_table", "expected_section"],
    [
        pytest.param(
            [["312", "3.123213"], ["280", "2.78897"], ["145", "1.34563546"]],
            Section(
                load=Load(load1=3.123213, load5=2.78897, load15=1.34563546),
                num_cpus=1,
            ),
            id="complete dataset",
        ),
        pytest.param(
            [["", "5,234"], ["234", ""], ["", ""]],
            Section(
                load=Load(load1=5.234, load5=2.34, load15=0),
                num_cpus=1,
            ),
            id="data missing",
        ),
    ],
)
def test_parse_ucd_cpu_load(string_table: StringTable, expected_section: Section) -> None:
    assert parse_ucd_cpu_load(string_table) == expected_section
