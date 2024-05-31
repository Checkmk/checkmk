#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from collections.abc import Iterable, Sequence

from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.sectionname import SectionName

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.inventory import InventoryPluginName
from cmk.checkengine.sectionparser import ParsedSectionName

from cmk.base.api.agent_based.plugin_classes import (
    AgentSectionPlugin,
    CheckPlugin,
    InventoryPlugin,
    SectionPlugin,
    SNMPSectionPlugin,
)
from cmk.base.api.agent_based.register.check_plugins import management_plugin_factory
from cmk.base.api.agent_based.register.section_plugins import trivial_section_factory
from cmk.base.api.agent_based.register.utils import validate_check_ruleset_item_consistency

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

# Lookup table for optimizing validate_check_ruleset_item_consistency()
_check_plugins_by_ruleset_name: dict[RuleSetName | None, list[CheckPlugin]] = defaultdict(list)

_sections_by_parsed_name: dict[ParsedSectionName, dict[SectionName, SectionPlugin]] = defaultdict(
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


def get_check_plugin(plugin_name: CheckPluginName) -> CheckPlugin | None:
    """Returns the registered check plug-in

    Management plugins may be created on the fly.
    """
    plugin = registered_check_plugins.get(plugin_name)
    if plugin is not None or not plugin_name.is_management_name():
        return plugin

    # create management board plug-in on the fly:
    non_mgmt_plugin = registered_check_plugins.get(plugin_name.create_basic_name())
    if non_mgmt_plugin is not None:
        mgmt_plugin = management_plugin_factory(non_mgmt_plugin)
        add_check_plugin(mgmt_plugin)
        return mgmt_plugin

    return None


def get_discovery_ruleset(ruleset_name: RuleSetName) -> Sequence[RuleSpec]:
    """Returns all rulesets of a given name"""
    return stored_rulesets.get(ruleset_name, [])


def get_host_label_ruleset(ruleset_name: RuleSetName) -> Sequence[RuleSpec]:
    """Returns all rulesets of a given name"""
    return stored_rulesets.get(ruleset_name, [])


def get_inventory_plugin(plugin_name: InventoryPluginName) -> InventoryPlugin | None:
    """Returns the registered inventory plug-in"""
    return registered_inventory_plugins.get(plugin_name)


def get_relevant_raw_sections(
    *,
    check_plugin_names: Iterable[CheckPluginName],
    inventory_plugin_names: Iterable[InventoryPluginName],
) -> dict[SectionName, SectionPlugin]:
    """return the raw sections potentially relevant for the given check or inventory plugins"""
    parsed_section_names: set[ParsedSectionName] = set()

    for check_plugin_name in check_plugin_names:
        if check_plugin := get_check_plugin(check_plugin_name):
            parsed_section_names.update(check_plugin.sections)

    for inventory_plugin_name in inventory_plugin_names:
        if inventory_plugin := get_inventory_plugin(inventory_plugin_name):
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


def get_section_producers(parsed_section_name: ParsedSectionName) -> set[SectionName]:
    return set(_sections_by_parsed_name[parsed_section_name])


def get_snmp_section_plugin(section_name: SectionName) -> SNMPSectionPlugin:
    return registered_snmp_sections[section_name]


def is_registered_check_plugin(check_plugin_name: CheckPluginName) -> bool:
    return check_plugin_name in registered_check_plugins


def is_registered_inventory_plugin(inventory_plugin_name: InventoryPluginName) -> bool:
    return inventory_plugin_name in registered_inventory_plugins


def is_registered_section_plugin(section_name: SectionName) -> bool:
    return is_registered_snmp_section_plugin(section_name) or is_registered_agent_section_plugin(
        section_name
    )


def is_registered_agent_section_plugin(section_name: SectionName) -> bool:
    return section_name in registered_agent_sections


def is_stored_ruleset(ruleset_name: RuleSetName) -> bool:
    return ruleset_name in stored_rulesets


def needs_redetection(section_name: SectionName) -> bool:
    section = get_section_plugin(section_name)
    return len(get_section_producers(section.parsed_section_name)) > 1


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
    rules: Sequence[RuleSpec],
) -> None:
    """Set a ruleset to a given value"""
    stored_rulesets[ruleset_name] = rules


def set_host_label_ruleset(ruleset_name: RuleSetName, rules: Sequence[RuleSpec]) -> None:
    """Set a ruleset to a given value"""
    stored_rulesets[ruleset_name] = rules


def is_registered_snmp_section_plugin(section_name: SectionName) -> bool:
    return section_name in registered_snmp_sections
