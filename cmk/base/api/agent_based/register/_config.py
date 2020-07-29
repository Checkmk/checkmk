#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Iterable, List, Optional, Set

import itertools

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import (
    CheckPluginName,
    InventoryPluginName,
    ParsedSectionName,
    SectionName,
)
from cmk.utils.check_utils import is_management_name, MANAGEMENT_NAME_PREFIX

from cmk.base.api.agent_based.type_defs import (
    AgentSectionPlugin,
    CheckPlugin,
    SectionPlugin,
    SNMPSectionPlugin,
)
from cmk.base.api.agent_based.register.check_plugins import management_plugin_factory
from cmk.base.api.agent_based.register.section_plugins import trivial_section_factory
from cmk.base.api.agent_based.register.utils import rank_sections_by_supersedes

registered_agent_sections: Dict[SectionName, AgentSectionPlugin] = {}
registered_snmp_sections: Dict[SectionName, SNMPSectionPlugin] = {}
registered_check_plugins: Dict[CheckPluginName, CheckPlugin] = {}


def add_check_plugin(check_plugin: CheckPlugin) -> None:
    registered_check_plugins[check_plugin.name] = check_plugin


def get_check_plugin(plugin_name: CheckPluginName) -> Optional[CheckPlugin]:
    """Returns the registered check plugin

    Management plugins may be created on the fly.
    """
    plugin = registered_check_plugins.get(plugin_name)
    if plugin is not None or not is_management_name(plugin_name):
        return plugin

    # create management board plugin on the fly:
    non_mgmt_name = CheckPluginName(str(plugin_name)[len(MANAGEMENT_NAME_PREFIX):])
    non_mgmt_plugin = registered_check_plugins.get(non_mgmt_name)
    if non_mgmt_plugin is not None:
        return management_plugin_factory(non_mgmt_plugin)

    return None


def get_parsed_section_creator(
        parsed_section_name: ParsedSectionName,
        available_raw_sections: List[SectionName]) -> Optional[SectionPlugin]:
    """return the section definition required to create the enquired parsed section"""
    section_defs = (get_section_plugin(n) for n in available_raw_sections)
    candidates = [
        p for p in section_defs if p is not None and p.parsed_section_name == parsed_section_name
    ]
    if not candidates:
        return None

    # We may still have more than one. The 'supersedes' feature should deal with that:
    # TODO (mo): CMK-4232 remove superseded ones
    plugins = candidates

    # validation should have enforced that this is exactly one.
    if not len(plugins) == 1:
        raise MKGeneralException("conflicting section definitions: %s" %
                                 ','.join(str(p) for p in plugins))
    return plugins[0]


def get_ranked_sections(
    available_raw_sections: Iterable[SectionName],
    filter_parsed_section: Optional[Set[ParsedSectionName]],
) -> List[SectionPlugin]:
    """
    Get the raw sections [that will be parsed into the required section] ordered by supersedings
    """
    return rank_sections_by_supersedes(
        ((name, get_section_plugin(name)) for name in available_raw_sections),
        filter_parsed_section,
    )


def get_relevant_raw_sections(
    *,
    check_plugin_names: Iterable[CheckPluginName] = (),
    inventory_plugin_names: Iterable[InventoryPluginName] = (),
) -> Dict[SectionName, SectionPlugin]:
    """return the raw sections potentially relevant for the given check or inventory plugins"""
    parsed_section_names: Set[ParsedSectionName] = set()

    for check_plugin_name in check_plugin_names:
        plugin = get_check_plugin(check_plugin_name)
        if plugin:
            parsed_section_names.update(plugin.sections)

    for inventory_plugin_name in inventory_plugin_names:
        # TODO (mo): once the inventory plugins are facing the new API,
        # this should look exactly as the block above!
        # For now: every inventory plugin name is exactly the parsed section name
        # Also TODO: add a few tests when this block is non-trivial.
        parsed_section_names.add(ParsedSectionName(str(inventory_plugin_name)))

    iter_all_sections: Iterable[SectionPlugin] = itertools.chain(
        iter_all_agent_sections(),
        iter_all_snmp_sections(),
    )

    return {
        section.name: section
        for section in iter_all_sections
        if section.parsed_section_name in parsed_section_names
    }


def get_section_plugin(section_name: SectionName) -> SectionPlugin:
    return (registered_agent_sections.get(section_name) or
            registered_snmp_sections.get(section_name) or trivial_section_factory(section_name))


def is_registered_check_plugin(check_plugin_name: CheckPluginName) -> bool:
    return check_plugin_name in registered_check_plugins


def is_registered_section_plugin(section_name: SectionName) -> bool:
    return section_name in registered_agent_sections or section_name in registered_snmp_sections


def iter_all_agent_sections() -> Iterable[AgentSectionPlugin]:
    return registered_agent_sections.values()  # pylint: disable=dict-values-not-iterating


def iter_all_check_plugins() -> Iterable[CheckPlugin]:
    return registered_check_plugins.values()  # pylint: disable=dict-values-not-iterating


def iter_all_snmp_sections() -> Iterable[SNMPSectionPlugin]:
    return registered_snmp_sections.values()  # pylint: disable=dict-values-not-iterating
