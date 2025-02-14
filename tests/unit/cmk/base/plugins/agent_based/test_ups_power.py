#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.testlib.snmp import snmp_is_detected

from cmk.utils.sectionname import SectionName

from cmk.base.plugins.agent_based import ups_power
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

# walks/usv-liebert
DATA0 = """
.1.3.6.1.2.1.1.2.0  .1.3.6.1.4.1.476.1.42
"""


@pytest.mark.usefixtures("fix_register")
def test_ups_power_detect(as_path: Callable[[str], Path]) -> None:
    assert snmp_is_detected(SectionName("ups_power"), as_path(DATA0))


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            [[["1", ""]]],
            {},
            id="empty power",
        ),
        pytest.param(
            [[["1", "2"]]],
            {"1": 2},
            id="power present",
        ),
        pytest.param(
            [[["1", "0"]]],
            {"1": 0},
            id="power is zero",
        ),
    ],
)
def test_ups_power_check(string_table: list[StringTable], section: dict[str, int]) -> None:
    assert ups_power.parse_ups_power(string_table) == section
