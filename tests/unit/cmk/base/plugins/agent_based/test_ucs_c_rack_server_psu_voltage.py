#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Service

SECTION = """
equipmentPsu	dn sys/rack-unit-7/psu-2	id 2	model UCSC-PSU1-1050W	operability operable	voltage ok
equipmentPsu	dn sys/switch-B/psu-1	id 1	model UCS-PSU-6332-AC	operability operable	voltage unknown
"""


def test_discovery_does_not_discover_UCS_voltage_unknown(fix_register: FixRegister) -> None:
    # see SUP-11285
    string_table = [line.split("\t") for line in SECTION.strip().split("\n")]
    discovery_function = fix_register.check_plugins[
        CheckPluginName("ucs_c_rack_server_psu_voltage")
    ].discovery_function
    parse_function = fix_register.agent_sections[
        SectionName("ucs_c_rack_server_psu")
    ].parse_function
    section = parse_function(string_table)
    assert list(discovery_function(section)) == [Service(item="Rack Unit 7 PSU 2")]
