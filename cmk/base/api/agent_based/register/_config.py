#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.sectionname import SectionName

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.inventory import InventoryPluginName

from cmk.base.api.agent_based.plugin_classes import (
    AgentSectionPlugin,
    CheckPlugin,
    InventoryPlugin,
    SectionPlugin,
    SNMPSectionPlugin,
)

registered_agent_sections: dict[SectionName, AgentSectionPlugin] = {}
registered_snmp_sections: dict[SectionName, SNMPSectionPlugin] = {}
registered_check_plugins: dict[CheckPluginName, CheckPlugin] = {}
registered_inventory_plugins: dict[InventoryPluginName, InventoryPlugin] = {}

# N O T E: This currently contains discovery *and* host_label rulesets.
# The rules are deliberately put the same dictionary, as we allow for
# the host_label_function and the discovery_function to share a ruleset.
# We provide separate API functions however, should the need arise to
# separate them.
stored_rulesets: dict[RuleSetName, Sequence[RuleSpec]] = {}


@dataclass(frozen=True)
class AgentBasedPlugins:
    agent_sections: Mapping[SectionName, AgentSectionPlugin]
    snmp_sections: Mapping[SectionName, SNMPSectionPlugin]
    check_plugins: Mapping[CheckPluginName, CheckPlugin]
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin]


def get_previously_loaded_plugins() -> AgentBasedPlugins:
    """Return the previously loaded agent-based plugins

    In the long run we want to get rid of this function and instead
    return the plugins directly after loading them (without registry).
    """
    return AgentBasedPlugins(
        agent_sections=registered_agent_sections,
        snmp_sections=registered_snmp_sections,
        check_plugins=registered_check_plugins,
        inventory_plugins=registered_inventory_plugins,
    )


def add_check_plugin(check_plugin: CheckPlugin) -> None:
    registered_check_plugins[check_plugin.name] = check_plugin


def add_discovery_ruleset(ruleset_name: RuleSetName) -> None:
    stored_rulesets.setdefault(ruleset_name, [])


def add_inventory_plugin(inventory_plugin: InventoryPlugin) -> None:
    registered_inventory_plugins[inventory_plugin.name] = inventory_plugin


def add_section_plugin(section_plugin: SectionPlugin) -> None:
    if isinstance(section_plugin, AgentSectionPlugin):
        registered_agent_sections[section_plugin.name] = section_plugin
    else:
        registered_snmp_sections[section_plugin.name] = section_plugin


def get_discovery_ruleset(ruleset_name: RuleSetName) -> Sequence[RuleSpec]:
    """Returns all rulesets of a given name"""
    return stored_rulesets.get(ruleset_name, [])


def get_host_label_ruleset(ruleset_name: RuleSetName) -> Sequence[RuleSpec]:
    """Returns all rulesets of a given name"""
    return stored_rulesets.get(ruleset_name, [])


def get_inventory_plugin(plugin_name: InventoryPluginName) -> InventoryPlugin | None:
    """Returns the registered inventory plug-in"""
    return registered_inventory_plugins.get(plugin_name)


def get_section_plugin(section_name: SectionName) -> SectionPlugin | None:
    return registered_agent_sections.get(section_name) or registered_snmp_sections.get(section_name)


def is_registered_inventory_plugin(inventory_plugin_name: InventoryPluginName) -> bool:
    return inventory_plugin_name in registered_inventory_plugins


def is_registered_section_plugin(section_name: SectionName) -> bool:
    return section_name in registered_snmp_sections or section_name in registered_agent_sections


def is_stored_ruleset(ruleset_name: RuleSetName) -> bool:
    return ruleset_name in stored_rulesets


def iter_all_discovery_rulesets() -> Iterable[RuleSetName]:
    return stored_rulesets.keys()


def set_discovery_ruleset(
    ruleset_name: RuleSetName,
    rules: Sequence[RuleSpec],
) -> None:
    """Set a ruleset to a given value"""
    stored_rulesets[ruleset_name] = rules
