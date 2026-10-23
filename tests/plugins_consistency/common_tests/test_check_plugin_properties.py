#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Collection, Sequence

from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    CheckPlugin,
    InventoryPlugin,
    ParsedSectionName,
)


def test_no_plugins_with_trivial_sections(agent_based_plugins: AgentBasedPlugins) -> None:
    """
    This is a sanity test for registered inventory and check plug-ins. It ensures that plugins
    have a non trivial section. Trivial sections may be created accidentally e.g. if a typo
    is introduced in the section or plug-in name.

    At runtime the checkengine will use a trivial parse function for those, but we consider it
    bad practice.
    """
    produced = {
        *(s.parsed_section_name for s in agent_based_plugins.agent_sections.values()),
        *(s.parsed_section_name for s in agent_based_plugins.snmp_sections.values()),
    }

    consumers: Sequence[CheckPlugin | InventoryPlugin] = [
        *agent_based_plugins.check_plugins.values(),
        *agent_based_plugins.inventory_plugins.values(),
    ]

    def _missing_sections(plugin: CheckPlugin | InventoryPlugin) -> Collection[ParsedSectionName]:
        return set(plugin.sections) - produced

    plugins_with_missing_sections = {
        plugin.name: missing for plugin in consumers if (missing := _missing_sections(plugin))
    }
    assert not plugins_with_missing_sections
