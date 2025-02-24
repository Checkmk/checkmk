#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Sequence
from importlib import import_module
from typing import assert_never

from cmk.utils.sectionname import SectionName

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.inventory import InventoryPluginName

from cmk.base.api.agent_based import plugin_classes as backend

from cmk import trace
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    entry_point_prefixes,
    InventoryPlugin,
    SimpleSNMPSection,
    SNMPSection,
)
from cmk.discover_plugins import discover_plugins, DiscoveredPlugins, PluginGroup, PluginLocation

from .check_plugins import create_check_plugin, get_check_plugin
from .inventory_plugins import create_inventory_plugin
from .section_plugins import create_agent_section_plugin, create_snmp_section_plugin

_ABPlugins = SimpleSNMPSection | SNMPSection | AgentSection | CheckPlugin | InventoryPlugin

tracer = trace.get_tracer()

registered_agent_sections: dict[SectionName, backend.AgentSectionPlugin] = {}
registered_snmp_sections: dict[SectionName, backend.SNMPSectionPlugin] = {}
registered_check_plugins: dict[CheckPluginName, backend.CheckPlugin] = {}
registered_inventory_plugins: dict[InventoryPluginName, backend.InventoryPlugin] = {}


def get_previously_loaded_plugins(errors: Sequence[str] = ()) -> backend.AgentBasedPlugins:
    """Return the previously loaded agent-based plugins

    In the long run we want to get rid of this function and instead
    return the plugins directly after loading them (without registry).
    """
    return backend.AgentBasedPlugins(
        agent_sections=registered_agent_sections,
        snmp_sections=registered_snmp_sections,
        check_plugins=registered_check_plugins,
        inventory_plugins=registered_inventory_plugins,
        errors=errors,
    )


def add_section_plugin(section_plugin: backend.SectionPlugin) -> None:
    if isinstance(section_plugin, backend.AgentSectionPlugin):
        registered_agent_sections[section_plugin.name] = section_plugin
    else:
        registered_snmp_sections[section_plugin.name] = section_plugin


def get_section_plugin(section_name: SectionName) -> backend.SectionPlugin | None:
    return registered_agent_sections.get(section_name) or registered_snmp_sections.get(section_name)


def is_registered_section_plugin(section_name: SectionName) -> bool:
    return section_name in registered_snmp_sections or section_name in registered_agent_sections


@tracer.instrument("load_all_plugins")
def load_all_plugins(
    sections: Iterable[backend.SNMPSectionPlugin | backend.AgentSectionPlugin],
    checks: Iterable[backend.CheckPlugin],
    *,
    legacy_errors: Iterable[str],
    raise_errors: bool,
) -> backend.AgentBasedPlugins:
    with tracer.span("discover_plugins"):
        discovered_plugins: DiscoveredPlugins[_ABPlugins] = discover_plugins(
            PluginGroup.AGENT_BASED, entry_point_prefixes(), raise_errors=raise_errors
        )

    errors = [
        *legacy_errors,
        *(f"Error in agent based plugin: {exc}" for exc in discovered_plugins.errors),
    ]

    with tracer.span("load_discovered_plugins"):
        for location, plugin in discovered_plugins.plugins.items():
            try:
                _register_plugin_by_type(location, plugin, validate=raise_errors)
            except Exception as exc:
                if raise_errors:
                    raise
                errors.append(f"Error in agent based plug-in {plugin.name} ({type(plugin)}): {exc}")

    _add_sections_to_register(sections)
    _add_checks_to_register(checks)
    return get_previously_loaded_plugins(errors)


def load_selected_plugins(
    locations: Iterable[PluginLocation],
    sections: Iterable[backend.SNMPSectionPlugin | backend.AgentSectionPlugin],
    checks: Iterable[backend.CheckPlugin],
    *,
    validate: bool,
) -> backend.AgentBasedPlugins:
    for location in locations:
        module = import_module(location.module)
        if location.name is not None:
            _register_plugin_by_type(location, getattr(module, location.name), validate=validate)
    _add_sections_to_register(sections)
    _add_checks_to_register(checks)
    return get_previously_loaded_plugins()


def _register_plugin_by_type(
    location: PluginLocation,
    plugin: AgentSection | SimpleSNMPSection | SNMPSection | CheckPlugin | InventoryPlugin,
    *,
    validate: bool,
) -> None:
    match plugin:
        case AgentSection():
            register_agent_section(plugin, location, validate=validate)
        case SimpleSNMPSection() | SNMPSection():
            register_snmp_section(plugin, location, validate=validate)
        case CheckPlugin():
            register_check_plugin(plugin, location)
        case InventoryPlugin():
            register_inventory_plugin(plugin, location)
        case unreachable:
            assert_never(unreachable)


def register_agent_section(
    section: AgentSection, location: PluginLocation, *, validate: bool
) -> None:
    section_plugin = create_agent_section_plugin(section, location, validate=validate)

    if (existing_section := get_section_plugin(section_plugin.name)) is not None:
        if existing_section.location == location:
            # This is relevant if we're loading the plugins twice:
            # Loading of v2 plugins is *not* a no-op the second time round.
            # But since we're storing the plugins in a global variable,
            # we must only raise, if this is not the *exact* same plugin.
            # once we stop storing the plugins in a global variable, this
            # special case can go.
            return

        raise ValueError(f"duplicate section definition: {section_plugin.name}")

    add_section_plugin(section_plugin)


def register_snmp_section(
    section: SimpleSNMPSection | SNMPSection, location: PluginLocation, *, validate: bool
) -> None:
    section_plugin = create_snmp_section_plugin(section, location, validate=validate)

    if (existing_section := get_section_plugin(section_plugin.name)) is not None:
        if existing_section.location == location:
            # This is relevant if we're loading the plugins twice:
            # Loading of v2 plugins is *not* a no-op the second time round.
            # But since we're storing the plugins in a global variable,
            # we must only raise, if this is not the *exact* same plugin.
            # once we stop storing the plugins in a global variable, this
            # special case can go.
            return
        raise ValueError(f"duplicate section definition: {section_plugin.name}")

    add_section_plugin(section_plugin)


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
        # sorry, but logwatch messes with the default parameters
        validate_kwargs=check.name not in {"logwatch_ec", "logwatch_ec_single"},
    )

    plugins_up_to_now = get_previously_loaded_plugins().check_plugins
    if (present := get_check_plugin(plugin.name, plugins_up_to_now)) is not None:
        if present.location == location:
            # This is relevant if we're loading the plugins twice:
            # Loading of v2 plugins is *not* a no-op the second time round.
            # But since we're storing the plugins in a global variable,
            # we must only raise, if this is not the *exact* same plugin.
            # once we stop storing the plugins in a global variable, this
            # special case can go.
            return
        raise ValueError(f"duplicate check plug-in definition: {plugin.name}")

    registered_check_plugins[plugin.name] = plugin


def register_inventory_plugin(inventory: InventoryPlugin, location: PluginLocation) -> None:
    plugin = create_inventory_plugin(
        name=inventory.name,
        sections=inventory.sections,
        inventory_function=inventory.inventory_function,
        inventory_default_parameters=inventory.inventory_default_parameters,
        inventory_ruleset_name=inventory.inventory_ruleset_name,
        location=location,
    )

    if (present := registered_inventory_plugins.get(plugin.name)) is not None:
        if present.location == location:
            # This is relevant if we're loading the plugins twice:
            # Loading of v2 plugins is *not* a no-op the second time round.
            # But since we're storing the plugins in a global variable,
            # we must only raise, if this is not the *exact* same plugin.
            # once we stop storing the plugins in a global variable, this
            # special case can go.
            return
        raise ValueError(f"duplicate inventory plug-in definition: {plugin.name}")

    registered_inventory_plugins[plugin.name] = plugin


def _add_sections_to_register(
    sections: Iterable[backend.SNMPSectionPlugin | backend.AgentSectionPlugin],
) -> None:
    for section in sections:
        if is_registered_section_plugin(section.name):
            continue
        add_section_plugin(section)


def _add_checks_to_register(
    checks: Iterable[backend.CheckPlugin],
) -> None:
    existing_plugins = get_previously_loaded_plugins().check_plugins
    for check in checks:
        present_plugin = existing_plugins.get(check.name)
        if present_plugin is not None and isinstance(present_plugin.location, PluginLocation):
            # location is PluginLocation => it's a new plug-in
            # (allow loading multiple times, e.g. update-config)
            # implemented here instead of the agent based register so that new API code does not
            # need to include any handling of legacy cases
            raise ValueError(
                f"Legacy check plug-in still exists for check plug-in {check.name}. "
                "Please remove legacy plug-in."
            )
        registered_check_plugins[check.name] = check
