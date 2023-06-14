#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import SectionName

from cmk.snmplib.type_defs import (  # pylint: disable=cmk-module-layer-violation
    BackendSNMPTree,
    SNMPDetectSpec,
)

from cmk.fetchers.snmp import (  # pylint: disable=cmk-module-layer-violation
    SNMPPluginStore,
    SNMPPluginStoreItem,
)

from ._config import (
    get_relevant_raw_sections,
    is_registered_snmp_section_plugin,
    iter_all_inventory_plugins,
    iter_all_snmp_sections,
)

__all__ = ["make_plugin_store"]


def _make_inventory_sections() -> frozenset[SectionName]:
    return frozenset(
        s
        for s in get_relevant_raw_sections(
            check_plugin_names=(),
            inventory_plugin_names=(p.name for p in iter_all_inventory_plugins()),
        )
        if is_registered_snmp_section_plugin(s)
    )


def make_plugin_store() -> SNMPPluginStore:
    inventory_sections = _make_inventory_sections()
    return SNMPPluginStore(
        {
            s.name: SNMPPluginStoreItem(
                [BackendSNMPTree.from_frontend(base=t.base, oids=t.oids) for t in s.trees],
                SNMPDetectSpec(s.detect_spec),
                s.name in inventory_sections,
            )
            for s in iter_all_snmp_sections()
        }
    )
