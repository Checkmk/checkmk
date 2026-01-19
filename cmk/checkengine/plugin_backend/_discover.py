#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="unreachable"

from collections.abc import Iterable
from importlib import import_module
from typing import assert_never

import cmk.trace
from cmk.agent_based import v2
from cmk.checkengine import plugins
from cmk.checkengine.plugins import SectionName
from cmk.discover_plugins import (
    discover_all_plugins,
    discover_plugins_from_modules,
    DiscoveredPlugins,
    PluginGroup,
    PluginLocation,
)

from .check_plugins import create_check_plugin
from .inventory_plugins import create_inventory_plugin
from .section_plugins import create_agent_section_plugin, create_snmp_section_plugin

_ABPlugins = (
    v2.SimpleSNMPSection | v2.SNMPSection | v2.AgentSection | v2.CheckPlugin | v2.InventoryPlugin
)

tracer = cmk.trace.get_tracer()


_NOT_YET_MOVED_PLUGINS = (
    # HACK for migrating plugins: also search in certain modules that are not yet moved.
    # This datastructure should only be filled for one commit in a chain, and be emptied
    # right away. This is for convenience of the reviewer of a plugin migration only:
    # This way we can separate migration and moving.
    # For example:
    # "cmk.base.legacy_checks.esx_vsphere_datastores",
    "cmk.base.legacy_checks.hyperv_checkpoints",
)


@tracer.instrument("load_all_plugins")
def load_all_plugins(
    sections: Iterable[plugins.SNMPSectionPlugin | plugins.AgentSectionPlugin],
    checks: Iterable[plugins.CheckPlugin],
    *,
    legacy_errors: Iterable[str],
    raise_errors: bool,
) -> plugins.AgentBasedPlugins:
    with tracer.span("discover_plugins"):
        discovered_plugins: DiscoveredPlugins[_ABPlugins] = discover_all_plugins(
            PluginGroup.AGENT_BASED, v2.entry_point_prefixes(), raise_errors=raise_errors
        )
        if _NOT_YET_MOVED_PLUGINS:
            more_discovered_plugins = discover_plugins_from_modules(
                v2.entry_point_prefixes(),
                _NOT_YET_MOVED_PLUGINS,
                raise_errors=raise_errors,
            )
            discovered_plugins = DiscoveredPlugins(
                [*discovered_plugins.errors, *more_discovered_plugins.errors],
                {**discovered_plugins.plugins, **more_discovered_plugins.plugins},
            )

    registered_agent_sections: dict[SectionName, plugins.AgentSectionPlugin] = {}
    registered_snmp_sections: dict[SectionName, plugins.SNMPSectionPlugin] = {}
    registered_check_plugins: dict[plugins.CheckPluginName, plugins.CheckPlugin] = {}
    registered_inventory_plugins: dict[plugins.InventoryPluginName, plugins.InventoryPlugin] = {}
    errors = [
        *legacy_errors,
        *(f"Error in agent based plugin: {exc}" for exc in discovered_plugins.errors),
    ]

    with tracer.span("load_discovered_plugins"):
        for location, plugin in discovered_plugins.plugins.items():
            try:
                _register_plugin_by_type(
                    location,
                    plugin,
                    registered_agent_sections,
                    registered_snmp_sections,
                    registered_check_plugins,
                    registered_inventory_plugins,
                    validate=raise_errors,
                )
            except Exception as exc:
                if raise_errors:
                    raise
                errors.append(f"Error in agent based plug-in {plugin.name} ({type(plugin)}): {exc}")

    _add_legacy_sections(sections, registered_agent_sections, registered_snmp_sections)
    _add_legacy_checks(checks, registered_check_plugins)
    return plugins.AgentBasedPlugins(
        agent_sections=registered_agent_sections,
        snmp_sections=registered_snmp_sections,
        check_plugins=registered_check_plugins,
        inventory_plugins=registered_inventory_plugins,
        errors=errors,
    )


def load_selected_plugins(
    locations: Iterable[PluginLocation],
    sections: Iterable[plugins.SNMPSectionPlugin | plugins.AgentSectionPlugin],
    checks: Iterable[plugins.CheckPlugin],
    *,
    validate: bool,
) -> plugins.AgentBasedPlugins:
    registered_agent_sections: dict[SectionName, plugins.AgentSectionPlugin] = {}
    registered_snmp_sections: dict[SectionName, plugins.SNMPSectionPlugin] = {}
    registered_check_plugins: dict[plugins.CheckPluginName, plugins.CheckPlugin] = {}
    registered_inventory_plugins: dict[plugins.InventoryPluginName, plugins.InventoryPlugin] = {}
    for location in locations:
        module = import_module(location.module)
        if location.name is not None:
            _register_plugin_by_type(
                location,
                getattr(module, location.name),
                registered_agent_sections,
                registered_snmp_sections,
                registered_check_plugins,
                registered_inventory_plugins,
                validate=validate,
            )
    _add_legacy_sections(sections, registered_agent_sections, registered_snmp_sections)
    _add_legacy_checks(checks, registered_check_plugins)
    return plugins.AgentBasedPlugins(
        agent_sections=registered_agent_sections,
        snmp_sections=registered_snmp_sections,
        check_plugins=registered_check_plugins,
        inventory_plugins=registered_inventory_plugins,
        errors=(),
    )


def _register_plugin_by_type(
    location: PluginLocation,
    plugin: v2.AgentSection
    | v2.SimpleSNMPSection
    | v2.SNMPSection
    | v2.CheckPlugin
    | v2.InventoryPlugin,
    registered_agent_sections: dict[SectionName, plugins.AgentSectionPlugin],
    registered_snmp_sections: dict[SectionName, plugins.SNMPSectionPlugin],
    registered_check_plugins: dict[plugins.CheckPluginName, plugins.CheckPlugin],
    registered_inventory_plugins: dict[plugins.InventoryPluginName, plugins.InventoryPlugin],
    *,
    validate: bool,
) -> None:
    match plugin:
        case v2.AgentSection():
            _register_agent_section(
                plugin,
                location,
                registered_agent_sections,
                registered_snmp_sections,
                validate=validate,
            )
        case v2.SimpleSNMPSection() | v2.SNMPSection():
            _register_snmp_section(
                plugin,
                location,
                registered_agent_sections,
                registered_snmp_sections,
                validate=validate,
            )
        case v2.CheckPlugin():
            _register_check_plugin(plugin, location, registered_check_plugins)
        case v2.InventoryPlugin():
            _register_inventory_plugin(plugin, location, registered_inventory_plugins)
        case unreachable:
            assert_never(unreachable)


def _register_agent_section(
    section: v2.AgentSection,
    location: PluginLocation,
    registered_agent_sections: dict[SectionName, plugins.AgentSectionPlugin],
    registered_snmp_sections: dict[SectionName, plugins.SNMPSectionPlugin],
    *,
    validate: bool,
) -> None:
    section_plugin = create_agent_section_plugin(section, location, validate=validate)

    if section_plugin.name in registered_agent_sections | registered_snmp_sections:
        raise ValueError(f"duplicate section definition: {section_plugin.name}")

    registered_agent_sections[section_plugin.name] = section_plugin


def _register_snmp_section(
    section: v2.SimpleSNMPSection | v2.SNMPSection,
    location: PluginLocation,
    registered_agent_sections: dict[SectionName, plugins.AgentSectionPlugin],
    registered_snmp_sections: dict[SectionName, plugins.SNMPSectionPlugin],
    *,
    validate: bool,
) -> None:
    section_plugin = create_snmp_section_plugin(section, location, validate=validate)

    if section_plugin.name in registered_agent_sections | registered_snmp_sections:
        raise ValueError(f"duplicate section definition: {section_plugin.name}")

    registered_snmp_sections[section_plugin.name] = section_plugin


def _register_check_plugin(
    check: v2.CheckPlugin,
    location: PluginLocation,
    registered_check_plugins: dict[plugins.CheckPluginName, plugins.CheckPlugin],
) -> None:
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

    if plugin.name in registered_check_plugins:
        raise ValueError(f"duplicate check plug-in definition: {plugin.name}")

    registered_check_plugins[plugin.name] = plugin


def _register_inventory_plugin(
    inventory: v2.InventoryPlugin,
    location: PluginLocation,
    registered_inventory_plugins: dict[plugins.InventoryPluginName, plugins.InventoryPlugin],
) -> None:
    plugin = create_inventory_plugin(
        name=inventory.name,
        sections=inventory.sections,
        inventory_function=inventory.inventory_function,
        inventory_default_parameters=inventory.inventory_default_parameters,
        inventory_ruleset_name=inventory.inventory_ruleset_name,
        location=location,
    )

    if plugin.name in registered_inventory_plugins:
        raise ValueError(f"duplicate inventory plug-in definition: {plugin.name}")

    registered_inventory_plugins[plugin.name] = plugin


def _add_legacy_sections(
    sections: Iterable[plugins.SNMPSectionPlugin | plugins.AgentSectionPlugin],
    registered_agent_sections: dict[SectionName, plugins.AgentSectionPlugin],
    registered_snmp_sections: dict[SectionName, plugins.SNMPSectionPlugin],
) -> None:
    for section in sections:
        if section.name in registered_agent_sections or section.name in registered_snmp_sections:
            continue
        if isinstance(section, plugins.AgentSectionPlugin):
            registered_agent_sections[section.name] = section
        else:
            registered_snmp_sections[section.name] = section


def _add_legacy_checks(
    checks: Iterable[plugins.CheckPlugin],
    registered_check_plugins: dict[plugins.CheckPluginName, plugins.CheckPlugin],
) -> None:
    for check in checks:
        if check.name in registered_check_plugins:
            continue
        registered_check_plugins[check.name] = check
