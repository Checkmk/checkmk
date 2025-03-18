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

from cmk.plugins.dell_powerconnect.agent_based.dell_powerconnect_temp import (
    snmp_section_dell_powerconnect_temp,
)

WALK = """
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.674.10895
.1.3.6.1.4.1.89.53.15.1.9 42
.1.3.6.1.4.1.89.53.15.1.10 1
"""


def test_temp_parse(
    as_path: Callable[[str], Path],
) -> None:
    snmp_walk = as_path(WALK)

    assert snmp_is_detected(snmp_section_dell_powerconnect_temp, snmp_walk)

    assert get_parsed_snmp_section(snmp_section_dell_powerconnect_temp, snmp_walk) == (42.0, "OK")
