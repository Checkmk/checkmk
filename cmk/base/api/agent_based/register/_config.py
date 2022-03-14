#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set

from cmk.utils.type_defs import (
    CheckPluginName,
    InventoryPluginName,
    ParsedSectionName,
    Ruleset,
    RuleSetName,
    SectionName,
)

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.inventory_classes import InventoryPlugin
from cmk.base.api.agent_based.register.check_plugins import management_plugin_factory
from cmk.base.api.agent_based.register.section_plugins import trivial_section_factory
from cmk.base.api.agent_based.register.utils import validate_check_ruleset_item_consistency
from cmk.base.api.agent_based.type_defs import AgentSectionPlugin, SectionPlugin, SNMPSectionPlugin

registered_agent_sections: Dict[SectionName, AgentSectionPlugin] = {}
registered_snmp_sections: Dict[SectionName, SNMPSectionPlugin] = {}
registered_check_plugins: Dict[CheckPluginName, CheckPlugin] = {}
registered_inventory_plugins: Dict[InventoryPluginName, InventoryPlugin] = {}

# N O T E: This currently contains discovery *and* host_label rulesets.
# The rules are deliberately put the same dictionary, as we allow for
# the host_label_function and the discovery_function to share a ruleset.
# We provide seperate API functions however, should the need arise to
# seperate them.
stored_rulesets: Dict[RuleSetName, Ruleset] = {}

# Lookup table for optimizing validate_check_ruleset_item_consistency()
_check_plugins_by_ruleset_name: Dict[Optional[RuleSetName], List[CheckPlugin]] = defaultdict(list)

_sections_by_parsed_name: Dict[ParsedSectionName, Dict[SectionName, SectionPlugin]] = defaultdict(
    dict
)


def add_check_plugin(check_plugin: CheckPlugin) -> None:
    validate_check_ruleset_item_consistency(check_plugin, _check_plugins_by_ruleset_name)
    registered_check_plugins[check_plugin.name] = check_plugin
    _check_plugins_by_ruleset_name[check_plugin.check_ruleset_name].append(check_plugin)


def add_discovery_ruleset(ruleset_name: RuleSetName) -> None:
    stored_rulesets.setdefault(ruleset_name, [])


def add_host_label_ruleset(ruleset_name: RuleSetName) -> None:
    stored_rulesets.setdefault(ruleset_name, [])


def add_inventory_plugin(inventory_plugin: InventoryPlugin) -> None:
    registered_inventory_plugins[inventory_plugin.name] = inventory_plugin


def add_section_plugin(section_plugin: SectionPlugin) -> None:
    _sections_by_parsed_name[section_plugin.parsed_section_name][
        section_plugin.name
    ] = section_plugin
    if isinstance(section_plugin, AgentSectionPlugin):
        registered_agent_sections[section_plugin.name] = section_plugin
    else:
        registered_snmp_sections[section_plugin.name] = section_plugin


def get_check_plugin(plugin_name: CheckPluginName) -> Optional[CheckPlugin]:
    """Returns the registered check plugin

    Management plugins may be created on the fly.
    """
    plugin = registered_check_plugins.get(plugin_name)
    if plugin is not None or not plugin_name.is_management_name():
        return plugin

    # create management board plugin on the fly:
    non_mgmt_plugin = registered_check_plugins.get(plugin_name.create_basic_name())
    if non_mgmt_plugin is not None:
        mgmt_plugin = management_plugin_factory(non_mgmt_plugin)
        add_check_plugin(mgmt_plugin)
        return mgmt_plugin

    return None


def get_discovery_ruleset(ruleset_name: RuleSetName) -> Ruleset:
    """Returns all rulesets of a given name"""
    return stored_rulesets.get(ruleset_name, [])


def get_host_label_ruleset(ruleset_name: RuleSetName) -> Ruleset:
    """Returns all rulesets of a given name"""
    return stored_rulesets.get(ruleset_name, [])


def get_inventory_plugin(plugin_name: InventoryPluginName) -> Optional[InventoryPlugin]:
    """Returns the registered inventory plugin"""
    return registered_inventory_plugins.get(plugin_name)


def get_relevant_raw_sections(
    *,
    check_plugin_names: Iterable[CheckPluginName],
    inventory_plugin_names: Iterable[InventoryPluginName],
) -> Dict[SectionName, SectionPlugin]:
    """return the raw sections potentially relevant for the given check or inventory plugins"""
    parsed_section_names: Set[ParsedSectionName] = set()

    for check_plugin_name in check_plugin_names:
        check_plugin = get_check_plugin(check_plugin_name)
        if check_plugin:
            parsed_section_names.update(check_plugin.sections)

    for inventory_plugin_name in inventory_plugin_names:
        inventory_plugin = get_inventory_plugin(inventory_plugin_name)
        if inventory_plugin:
            parsed_section_names.update(inventory_plugin.sections)

    return {
        section_name: section
        for parsed_name in parsed_section_names
        for section_name, section in _sections_by_parsed_name[parsed_name].items()
    }


def get_section_plugin(section_name: SectionName) -> SectionPlugin:
    return (
        registered_agent_sections.get(section_name)
        or registered_snmp_sections.get(section_name)
        or trivial_section_factory(section_name)
    )


def get_section_producers(parsed_section_name: ParsedSectionName) -> Set[SectionName]:
    return set(_sections_by_parsed_name[parsed_section_name])


def get_snmp_section_plugin(section_name: SectionName) -> SNMPSectionPlugin:
    return registered_snmp_sections[section_name]


def is_registered_check_plugin(check_plugin_name: CheckPluginName) -> bool:
    return check_plugin_name in registered_check_plugins


def is_registered_inventory_plugin(inventory_plugin_name: InventoryPluginName) -> bool:
    return inventory_plugin_name in registered_inventory_plugins


def is_registered_section_plugin(section_name: SectionName) -> bool:
    return section_name in registered_agent_sections or section_name in registered_snmp_sections


def iter_all_agent_sections() -> Iterable[AgentSectionPlugin]:
    return registered_agent_sections.values()


def iter_all_check_plugins() -> Iterable[CheckPlugin]:
    return registered_check_plugins.values()


def iter_all_discovery_rulesets() -> Iterable[RuleSetName]:
    return stored_rulesets.keys()


def iter_all_host_label_rulesets() -> Iterable[RuleSetName]:
    return stored_rulesets.keys()


def iter_all_inventory_plugins() -> Iterable[InventoryPlugin]:
    return registered_inventory_plugins.values()


def iter_all_snmp_sections() -> Iterable[SNMPSectionPlugin]:
    return registered_snmp_sections.values()


def len_snmp_sections() -> int:
    return len(registered_snmp_sections)


def set_discovery_ruleset(
    ruleset_name: RuleSetName,
    rules: Ruleset,
) -> None:
    """Set a ruleset to a given value"""
    stored_rulesets[ruleset_name] = rules


def set_host_label_ruleset(
    ruleset_name: RuleSetName,
    rules: Ruleset,
) -> None:
    """Set a ruleset to a given value"""
    stored_rulesets[ruleset_name] = rules


def is_registered_snmp_section_plugin(section_name: SectionName) -> bool:
    return section_name in registered_snmp_sections
