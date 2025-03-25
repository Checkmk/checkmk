#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkengine.plugins import InventoryPlugin
from cmk.checkengine.sectionparser import ParsedSectionName

from cmk.base.api.agent_based.plugin_classes import (
    AgentBasedPlugins,
    CheckPlugin,
)


def test_no_plugins_with_trivial_sections(agent_based_plugins: AgentBasedPlugins) -> None:
    """
    This is a sanity test for registered inventory and check plug-ins. It ensures that plugins
    have a non trivial section. Trivial sections may be created accidentally e.g. if a typo
    is introduced in the section or plug-in name during the migration to the new API. If a
    trivial section without a parse_function is sufficient for your plug-in you have to add it
    to the known exceptions below.
    """
    known_exceptions: set[ParsedSectionName] = set()  # currently no exceptions!

    # agent_based_plugins does not include trivial sections created by the trivial_section_factory
    registered_sections = {
        *(s.parsed_section_name for s in agent_based_plugins.agent_sections.values()),
        *(s.parsed_section_name for s in agent_based_plugins.snmp_sections.values()),
    }

    registered_check_and_inventory_plugins: list[CheckPlugin | InventoryPlugin] = [
        *agent_based_plugins.check_plugins.values(),
        *agent_based_plugins.inventory_plugins.values(),
    ]

    sections_ok_to_subscribe_to = registered_sections | known_exceptions
    all_subscribed_sections = {
        s for plugin in registered_check_and_inventory_plugins for s in plugin.sections
    }

    # make sure this test is up to date:
    outdated_exceptions = (known_exceptions & registered_sections) | (
        known_exceptions - all_subscribed_sections
    )
    assert not outdated_exceptions

    if all_subscribed_sections < sections_ok_to_subscribe_to:
        return

    plugins_with_trivial_sections = {
        plugin.name: unknown_sections
        for plugin in registered_check_and_inventory_plugins
        if (
            unknown_sections := [s for s in plugin.sections if s not in sections_ok_to_subscribe_to]
        )
    }

    msg = "\n".join(
        f"{plugin}: {', '.join(str(s) for s in sections)}"
        for plugin, sections in plugins_with_trivial_sections.items()
    )
    assert 0, f"""Found new plug-ins with trivial sections:
PLUGIN - TRIVIAL SECTIONS'
----------------
{msg}"""
