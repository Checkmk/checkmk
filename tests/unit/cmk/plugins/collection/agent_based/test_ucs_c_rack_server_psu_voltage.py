#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.sectionname import SectionName

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.register import AgentBasedPlugins

from cmk.agent_based.v2 import Service

SECTION = """
equipmentPsu	dn sys/rack-unit-7/psu-2	id 2	model UCSC-PSU1-1050W	operability operable	voltage ok
equipmentPsu	dn sys/switch-B/psu-1	id 1	model UCS-PSU-6332-AC	operability operable	voltage unknown
"""


def test_discovery_does_not_discover_UCS_voltage_unknown(
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    # see SUP-11285
    string_table = [line.split("\t") for line in SECTION.strip().split("\n")]
    discovery_function = agent_based_plugins.check_plugins[
        CheckPluginName("ucs_c_rack_server_psu_voltage")
    ].discovery_function
    parse_function = agent_based_plugins.agent_sections[
        SectionName("ucs_c_rack_server_psu")
    ].parse_function
    section = parse_function(string_table)
    assert list(discovery_function(section)) == [Service(item="Rack Unit 7 PSU 2")]
