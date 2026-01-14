#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.ucs_c_rack_server_psu import (
    discover_ucs_c_rack_server_psu_voltage,
    parse_ucs_c_rack_server_psu,
)

SECTION = """
equipmentPsu	dn sys/rack-unit-7/psu-2	id 2	model UCSC-PSU1-1050W	operability operable	voltage ok
equipmentPsu	dn sys/switch-B/psu-1	id 1	model UCS-PSU-6332-AC	operability operable	voltage unknown
"""


def test_discovery_does_not_discover_UCS_voltage_unknown() -> None:
    # see SUP-11285
    string_table = [line.split("\t") for line in SECTION.strip().split("\n")]
    section = parse_ucs_c_rack_server_psu(string_table)
    result = list(discover_ucs_c_rack_server_psu_voltage(section))
    assert result == [("Rack Unit 7 PSU 2", {})]
