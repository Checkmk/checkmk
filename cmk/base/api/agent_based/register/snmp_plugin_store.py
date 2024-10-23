#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.sectionname import SectionName

from cmk.snmplib import (
    BackendSNMPTree,  # pylint: disable=cmk-module-layer-violation
    SNMPDetectSpec,  # pylint: disable=cmk-module-layer-violation
)

from cmk.fetchers.snmp import (  # pylint: disable=cmk-module-layer-violation
    SNMPPluginStore,
    SNMPPluginStoreItem,
)

from ._config import (
    AgentBasedPlugins,
    get_relevant_raw_sections,
)

__all__ = ["make_plugin_store"]


def _make_inventory_sections(plugins: AgentBasedPlugins) -> frozenset[SectionName]:
    return frozenset(
        s
        for s in get_relevant_raw_sections(  # this will need to know all the plugins soon.
            check_plugin_names=(),
            inventory_plugin_names=plugins.inventory_plugins,
        )
        if s in plugins.snmp_sections
    )


def make_plugin_store(plugins: AgentBasedPlugins) -> SNMPPluginStore:
    inventory_sections = _make_inventory_sections(plugins)
    return SNMPPluginStore(
        {
            s.name: SNMPPluginStoreItem(
                [BackendSNMPTree.from_frontend(base=t.base, oids=t.oids) for t in s.trees],
                SNMPDetectSpec(s.detect_spec),
                s.name in inventory_sections,
            )
            for s in plugins.snmp_sections.values()
        }
    )
