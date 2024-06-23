#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import assert_never

import cmk.utils.debug
from cmk.utils.plugin_loader import load_plugins_with_exceptions

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    entry_point_prefixes,
    InventoryPlugin,
    SimpleSNMPSection,
    SNMPSection,
)
from cmk.discover_plugins import discover_plugins, DiscoveredPlugins, PluginGroup, PluginLocation

from ._config import (
    add_check_plugin,
    add_discovery_ruleset,
    add_host_label_ruleset,
    add_inventory_plugin,
    add_section_plugin,
    get_check_plugin,
    get_inventory_plugin,
    get_section_plugin,
    is_registered_check_plugin,
    is_registered_inventory_plugin,
    is_registered_section_plugin,
)
from .check_plugins import create_check_plugin
from .inventory_plugins import create_inventory_plugin
from .section_plugins import create_agent_section_plugin, create_snmp_section_plugin

_ABPlugins = SimpleSNMPSection | SNMPSection | AgentSection | CheckPlugin | InventoryPlugin


def load_all_plugins() -> list[str]:
    raise_errors = cmk.utils.debug.enabled()
    errors = []
    for plugin_name, exception in load_plugins_with_exceptions("cmk.base.plugins.agent_based"):
        errors.append(f"Error in agent based plug-in {plugin_name}: {exception}")
        if raise_errors:
            raise exception

    discovered_plugins: DiscoveredPlugins[_ABPlugins] = discover_plugins(
        PluginGroup.AGENT_BASED, entry_point_prefixes(), raise_errors=raise_errors
    )
    errors.extend(f"Error in agent based plugin: {exc}" for exc in discovered_plugins.errors)
    for location, plugin in discovered_plugins.plugins.items():
        try:
            register_plugin_by_type(location, plugin)
        except Exception as exc:
            if raise_errors:
                raise
            errors.append(
                f"Error in agent based plug-in {plugin.name} ({type(plugin).__name__}): {exc}"
            )

    return errors


def register_plugin_by_type(
    location: PluginLocation,
    plugin: AgentSection | SimpleSNMPSection | SNMPSection | CheckPlugin | InventoryPlugin,
) -> None:
    match plugin:
        case AgentSection():
            register_agent_section(plugin, location)
        case SimpleSNMPSection() | SNMPSection():
            register_snmp_section(plugin, location)
        case CheckPlugin():
            register_check_plugin(plugin, location)
        case InventoryPlugin():
            register_inventory_plugin(plugin, location)
        case unreachable:
            assert_never(unreachable)


def register_agent_section(section: AgentSection, location: PluginLocation) -> None:
    section_plugin = create_agent_section_plugin(
        section, location, validate=cmk.utils.debug.enabled()
    )

    if is_registered_section_plugin(section_plugin.name):
        if get_section_plugin(section_plugin.name).location == location:
            # This is relevant if we're loading the plugins twice:
            # Loading of v2 plugins is *not* a no-op the second time round.
            # But since we're storing the plugins in a global variable,
            # we must only raise, if this is not the *exact* same plugin.
            # once we stop storing the plugins in a global variable, this
            # special case can go.
            return

        raise ValueError(f"duplicate section definition: {section_plugin.name}")

    add_section_plugin(section_plugin)
    if section_plugin.host_label_ruleset_name is not None:
        add_host_label_ruleset(section_plugin.host_label_ruleset_name)


def register_snmp_section(
    section: SimpleSNMPSection | SNMPSection, location: PluginLocation
) -> None:
    section_plugin = create_snmp_section_plugin(
        section, location, validate=cmk.utils.debug.enabled()
    )

    if is_registered_section_plugin(section_plugin.name):
        if get_section_plugin(section_plugin.name).location == location:
            # This is relevant if we're loading the plugins twice:
            # Loading of v2 plugins is *not* a no-op the second time round.
            # But since we're storing the plugins in a global variable,
            # we must only raise, if this is not the *exact* same plugin.
            # once we stop storing the plugins in a global variable, this
            # special case can go.
            return
        raise ValueError(f"duplicate section definition: {section_plugin.name}")

    add_section_plugin(section_plugin)
    if section_plugin.host_label_ruleset_name is not None:
        add_host_label_ruleset(section_plugin.host_label_ruleset_name)


def register_check_plugin(check: CheckPlugin, location: PluginLocation) -> None:
    plugin = create_check_plugin(
        name=check.name,
        sections=check.sections,
        service_name=check.service_name,
        discovery_function=check.discovery_function,
        discovery_default_parameters=check.discovery_default_parameters,
        discovery_ruleset_name=check.discovery_ruleset_name,
        discovery_ruleset_type=check.discovery_ruleset_type,
        check_function=check.check_function,
        check_default_parameters=check.check_default_parameters,
        check_ruleset_name=check.check_ruleset_name,
        cluster_check_function=check.cluster_check_function,
        location=location,
    )

    if is_registered_check_plugin(plugin.name):
        if (present := get_check_plugin(plugin.name)) is not None and present.location == location:
            # This is relevant if we're loading the plugins twice:
            # Loading of v2 plugins is *not* a no-op the second time round.
            # But since we're storing the plugins in a global variable,
            # we must only raise, if this is not the *exact* same plugin.
            # once we stop storing the plugins in a global variable, this
            # special case can go.
            return
        raise ValueError(f"duplicate check plug-in definition: {plugin.name}")

    add_check_plugin(plugin)
    if plugin.discovery_ruleset_name is not None:
        add_discovery_ruleset(plugin.discovery_ruleset_name)


def register_inventory_plugin(inventory: InventoryPlugin, location: PluginLocation) -> None:
    plugin = create_inventory_plugin(
        name=inventory.name,
        sections=inventory.sections,
        inventory_function=inventory.inventory_function,
        inventory_default_parameters=inventory.inventory_default_parameters,
        inventory_ruleset_name=inventory.inventory_ruleset_name,
        location=location,
    )

    if is_registered_inventory_plugin(plugin.name):
        if (
            present := get_inventory_plugin(plugin.name)
        ) is not None and present.location == location:
            # This is relevant if we're loading the plugins twice:
            # Loading of v2 plugins is *not* a no-op the second time round.
            # But since we're storing the plugins in a global variable,
            # we must only raise, if this is not the *exact* same plugin.
            # once we stop storing the plugins in a global variable, this
            # special case can go.
            return
        raise ValueError(f"duplicate inventory plug-in definition: {plugin.name}")

    add_inventory_plugin(plugin)
