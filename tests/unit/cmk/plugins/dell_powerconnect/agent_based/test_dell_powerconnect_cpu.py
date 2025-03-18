#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path

from tests.unit.cmk.plugins.collection.agent_based.snmp import (
    get_parsed_snmp_section,
    snmp_is_detected,
)

from cmk.plugins.dell_powerconnect.agent_based.dell_powerconnect_cpu import (
    snmp_section_dell_powerconnect_cpu,
)

WALK = """
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.674.10895
.1.3.6.1.4.1.89.1.6 1
.1.3.6.1.4.1.89.1.7 91
.1.3.6.1.4.1.89.1.8 10
.1.3.6.1.4.1.89.1.9 4
"""


def test_cpu_parse(
    as_path: Callable[[str], Path],
) -> None:
    snmp_walk = as_path(WALK)

    assert snmp_is_detected(snmp_section_dell_powerconnect_cpu, snmp_walk)

    assert get_parsed_snmp_section(snmp_section_dell_powerconnect_cpu, snmp_walk) == [
        ["1", "91", "10", "4"]
    ]
