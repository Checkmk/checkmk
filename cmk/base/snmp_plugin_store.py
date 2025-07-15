#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.fetchers.snmp import SNMPPluginStore, SNMPPluginStoreItem
from cmk.snmplib import BackendSNMPTree, SNMPDetectSpec

__all__ = ["make_plugin_store"]


def make_plugin_store(plugins: AgentBasedPlugins) -> SNMPPluginStore:
    parsed_sections_relevant_for_inventory = {
        section_name
        for plugin in plugins.inventory_plugins.values()
        for section_name in plugin.sections
    }
    return SNMPPluginStore(
        {
            s.name: SNMPPluginStoreItem(
                [BackendSNMPTree.from_frontend(base=t.base, oids=t.oids) for t in s.trees],
                SNMPDetectSpec(s.detect_spec),
                s.parsed_section_name in parsed_sections_relevant_for_inventory,
            )
            for s in plugins.snmp_sections.values()
        }
    )
