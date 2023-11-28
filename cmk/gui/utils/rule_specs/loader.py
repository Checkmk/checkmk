#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass

from cmk.utils.version import Edition

from cmk.discover_plugins import discover_plugins, DiscoveredPlugins, PluginGroup
from cmk.rulesets.v1 import (
    ActiveChecksRuleSpec,
    AgentConfigRuleSpec,
    CheckParameterRuleSpecWithItem,
    CheckParameterRuleSpecWithoutItem,
    EnforcedServiceRuleSpecWithItem,
    EnforcedServiceRuleSpecWithoutItem,
    ExtraHostConfRuleSpec,
    ExtraServiceConfRuleSpec,
    HostRuleSpec,
    InventoryParameterRuleSpec,
    ServiceRuleSpec,
    SpecialAgentRuleSpec,
)

RuleSpec = (
    HostRuleSpec
    | ServiceRuleSpec
    | CheckParameterRuleSpecWithItem
    | CheckParameterRuleSpecWithoutItem
    | EnforcedServiceRuleSpecWithItem
    | EnforcedServiceRuleSpecWithoutItem
    | InventoryParameterRuleSpec
    | ActiveChecksRuleSpec
    | AgentConfigRuleSpec
    | SpecialAgentRuleSpec
    | ExtraHostConfRuleSpec
    | ExtraServiceConfRuleSpec
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
            HostRuleSpec: "rule_spec_",
            ServiceRuleSpec: "rule_spec_",
            CheckParameterRuleSpecWithItem: "rule_spec_",
            CheckParameterRuleSpecWithoutItem: "rule_spec_",
            EnforcedServiceRuleSpecWithItem: "rule_spec_",
            EnforcedServiceRuleSpecWithoutItem: "rule_spec_",
            InventoryParameterRuleSpec: "rule_spec_",
            ActiveChecksRuleSpec: "rule_spec_",
            AgentConfigRuleSpec: "rule_spec_",
            SpecialAgentRuleSpec: "rule_spec_",
            ExtraHostConfRuleSpec: "rule_spec_",
            ExtraServiceConfRuleSpec: "rule_spec_",
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
        if isinstance(plugin, CheckParameterRuleSpecWithItem) and plugin.create_enforced_service:
            loaded.append(
                LoadedRuleSpec(
                    rule_spec=EnforcedServiceRuleSpecWithItem(
                        title=plugin.title,
                        topic=plugin.topic,
                        parameter_form=plugin.parameter_form,
                        item_form=plugin.item_form,
                        name=plugin.name,
                        is_deprecated=plugin.is_deprecated,
                        help_text=plugin.help_text,
                    ),
                    edition_only=_get_edition_only(location.module),
                )
            )
        elif (
            isinstance(plugin, CheckParameterRuleSpecWithoutItem) and plugin.create_enforced_service
        ):
            loaded.append(
                LoadedRuleSpec(
                    rule_spec=EnforcedServiceRuleSpecWithoutItem(
                        title=plugin.title,
                        topic=plugin.topic,
                        parameter_form=plugin.parameter_form,
                        name=plugin.name,
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
