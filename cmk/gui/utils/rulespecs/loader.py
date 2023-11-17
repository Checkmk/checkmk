#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.discover_plugins import discover_plugins, DiscoveredPlugins
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


def load_api_v1_rulespecs(
    raise_errors: bool,
) -> tuple[Sequence[str], Sequence[RuleSpec]]:
    discovered_plugins: DiscoveredPlugins[RuleSpec] = discover_plugins(
        "rulesets",
        {
            HostRuleSpec: "rulespec_",
            ServiceRuleSpec: "rulespec_",
            CheckParameterRuleSpecWithItem: "rulespec_",
            CheckParameterRuleSpecWithoutItem: "rulespec_",
            EnforcedServiceRuleSpecWithItem: "rulespec_",
            EnforcedServiceRuleSpecWithoutItem: "rulespec_",
            InventoryParameterRuleSpec: "rulespec_",
            ActiveChecksRuleSpec: "rulespec_",
            AgentConfigRuleSpec: "rulespec_",
            SpecialAgentRuleSpec: "rulespec_",
            ExtraHostConfRuleSpec: "rulespec_",
            ExtraServiceConfRuleSpec: "rulespec_",
        },
        raise_errors=raise_errors,
    )

    errors = [str(e) for e in discovered_plugins.errors]
    loaded = [
        *discovered_plugins.plugins.values(),
        *_generate_additional_plugins(discovered_plugins),
    ]
    # TODO:
    #  * see if we really need to return the errors. Maybe we can just either ignore or raise them.
    return errors, loaded


def _generate_additional_plugins(
    discovered_plugins: DiscoveredPlugins[RuleSpec],
) -> Sequence[RuleSpec]:
    loaded: list[RuleSpec] = []
    for plugin in discovered_plugins.plugins.values():
        if isinstance(plugin, CheckParameterRuleSpecWithItem) and plugin.create_enforced_service:
            loaded.append(
                EnforcedServiceRuleSpecWithItem(
                    title=plugin.title,
                    topic=plugin.topic,
                    value_spec=plugin.value_spec,
                    item=plugin.item,
                    name=plugin.name,
                    is_deprecated=plugin.is_deprecated,
                    help_text=plugin.help_text,
                )
            )
        elif (
            isinstance(plugin, CheckParameterRuleSpecWithoutItem) and plugin.create_enforced_service
        ):
            loaded.append(
                EnforcedServiceRuleSpecWithoutItem(
                    title=plugin.title,
                    topic=plugin.topic,
                    value_spec=plugin.value_spec,
                    name=plugin.name,
                    is_deprecated=plugin.is_deprecated,
                    help_text=plugin.help_text,
                )
            )
    return loaded
