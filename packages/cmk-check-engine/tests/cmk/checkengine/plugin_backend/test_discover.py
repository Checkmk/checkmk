#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import AgentSection, SimpleSNMPSection, SNMPTree, startswith, StringTable
from cmk.checkengine.plugin_backend import load_discovered_plugins
from cmk.discover_plugins import DiscoveredPlugins, PluginConflict, PluginLocation


def _parse(string_table: StringTable) -> StringTable:
    return string_table


def test_section_name_conflict_across_section_types_is_reported() -> None:
    agent_location = PluginLocation("cmk.plugins.foo.agent_based.foo", "agent_section_foo")
    snmp_location = PluginLocation("cmk_addons.plugins.foo.agent_based.foo", "snmp_section_foo")
    discovered = DiscoveredPlugins[
        AgentSection[StringTable] | SimpleSNMPSection[StringTable, StringTable]
    ](
        errors=(),
        plugins={
            agent_location: AgentSection(name="foo", parse_function=_parse),
            snmp_location: SimpleSNMPSection(
                name="foo",
                parse_function=_parse,
                detect=startswith(".1.3.6.1.2.1.1.1.0", "foo"),
                fetch=SNMPTree(base=".1.3.6.1.4.1.1", oids=["1"]),
            ),
        },
        conflicts=(),
        errors_by_module={},
    )

    plugins = load_discovered_plugins(discovered, raise_errors=False)

    assert plugins.conflicts == [PluginConflict("foo", used=agent_location, ignored=snmp_location)]
