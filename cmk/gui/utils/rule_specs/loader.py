#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass

from cmk.utils.version import Edition

from cmk.discover_plugins import discover_plugins, DiscoveredPlugins, PluginGroup
from cmk.rulesets.v1.rule_specs import (
    ActiveCheck,
    AgentAccess,
    AgentConfig,
    CheckParameters,
    DiscoveryParameters,
    EnforcedService,
    ExtraHostConfEventConsole,
    ExtraHostConfHostMonitoring,
    ExtraServiceConf,
    Host,
    InventoryParameters,
    NotificationParameters,
    Service,
    SNMP,
    SpecialAgent,
)

RuleSpec = (
    ActiveCheck
    | AgentConfig
    | AgentAccess
    | EnforcedService
    | ExtraServiceConf
    | ExtraHostConfHostMonitoring
    | ExtraHostConfEventConsole
    | CheckParameters
    | Host
    | InventoryParameters
    | NotificationParameters
    | DiscoveryParameters
    | Service
    | SNMP
    | SpecialAgent
)


@dataclass(frozen=True)
class LoadedRuleSpec:
    rule_spec: RuleSpec
    edition_only: Edition


def load_api_v1_rule_specs(
    raise_errors: bool,
) -> tuple[Sequence[str], Sequence[LoadedRuleSpec]]:
    discovered_plugins: DiscoveredPlugins[RuleSpec] = discover_plugins(
        PluginGroup.RULESETS,
        {
            ActiveCheck: "rule_spec_",
            AgentConfig: "rule_spec_",
            AgentAccess: "rule_spec_",
            EnforcedService: "rule_spec_",
            ExtraServiceConf: "rule_spec_",
            ExtraHostConfHostMonitoring: "rule_spec_",
            ExtraHostConfEventConsole: "rule_spec_",
            CheckParameters: "rule_spec_",
            Host: "rule_spec_",
            InventoryParameters: "rule_spec_",
            NotificationParameters: "rule_spec_",
            DiscoveryParameters: "rule_spec_",
            Service: "rule_spec_",
            SNMP: "rule_spec_",
            SpecialAgent: "rule_spec_",
        },
        raise_errors=raise_errors,
    )

    errors = [str(e) for e in discovered_plugins.errors]

    loaded_plugins = [
        LoadedRuleSpec(rule_spec=plugin, edition_only=_get_edition_only(location.module))
        for location, plugin in discovered_plugins.plugins.items()
    ]
    loaded = [
        *loaded_plugins,
        *_generate_additional_plugins(discovered_plugins),
    ]
    # TODO:
    #  * see if we really need to return the errors. Maybe we can just either ignore or raise them.
    return errors, loaded


def _generate_additional_plugins(
    discovered_plugins: DiscoveredPlugins[RuleSpec],
) -> Sequence[LoadedRuleSpec]:
    loaded: list[LoadedRuleSpec] = []
    for location, plugin in discovered_plugins.plugins.items():
        if isinstance(plugin, CheckParameters) and plugin.create_enforced_service:
            loaded.append(
                LoadedRuleSpec(
                    rule_spec=EnforcedService(
                        title=plugin.title,
                        topic=plugin.topic,
                        parameter_form=plugin.parameter_form,
                        name=plugin.name,
                        condition=plugin.condition,
                        is_deprecated=plugin.is_deprecated,
                        help_text=plugin.help_text,
                    ),
                    edition_only=_get_edition_only(location.module),
                )
            )
    return loaded


def _get_edition_only(plugin_module: str) -> Edition:
    """
    >>> _get_edition_only('cmk.plugins.family.rulesets.module_name')
    <Edition.CRE: _EditionValue(short='cre', long='raw', title='Checkmk Raw Edition')>
    >>> _get_edition_only('cmk.plugins.family.rulesets.cce')
    <Edition.CCE: _EditionValue(short='cce', long='cloud', title='Checkmk Cloud Edition')>
    """
    edition_folder = plugin_module.split(".")[-1]
    for edition in Edition:
        if edition_folder == edition.short:
            return edition
    return Edition.CRE
