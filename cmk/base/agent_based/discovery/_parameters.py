#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal

from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.type_defs import HostName, RuleSetName

from cmk.checkers import PDiscoveryPlugin, PHostLabelDiscoveryPlugin

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.type_defs import Parameters, ParametersTypeAlias
from cmk.base.config import ConfigCache

__all__ = ["get_discovery_parameters", "get_host_label_parameters"]


def _get_plugin_parameters(
    host_name: HostName,
    config_cache: ConfigCache,
    *,
    default_parameters: ParametersTypeAlias | None,
    ruleset_name: RuleSetName | None,
    ruleset_type: Literal["all", "merged"],
    rules_getter_function: Callable[[RuleSetName], Sequence[RuleSpec]],
) -> None | Parameters | list[Parameters]:
    if default_parameters is None:
        # This means the function will not accept any params.
        return None
    if ruleset_name is None:
        # This means we have default params, but no rule set.
        # Not very sensical for discovery functions, but not forbidden by the API either.
        return Parameters(default_parameters)

    rules = rules_getter_function(ruleset_name)

    if ruleset_type == "all":
        host_rules = config_cache.host_extra_conf(host_name, rules)
        host_rules.append(default_parameters)
        return [Parameters(d) for d in host_rules]

    if ruleset_type == "merged":
        return Parameters(
            {
                **default_parameters,
                **config_cache.host_extra_conf_merged(host_name, rules),
            }
        )

    # validation should have prevented this
    raise NotImplementedError(f"unknown discovery rule set type {ruleset_type!r}")


def get_discovery_parameters(
    host_name: HostName,
    config_cache: ConfigCache,
    plugin: PDiscoveryPlugin,
) -> None | Parameters | list[Parameters]:
    return _get_plugin_parameters(
        host_name,
        config_cache,
        default_parameters=plugin.discovery_default_parameters,
        ruleset_name=plugin.discovery_ruleset_name,
        ruleset_type=plugin.discovery_ruleset_type,
        rules_getter_function=agent_based_register.get_discovery_ruleset,
    )


def get_host_label_parameters(
    host_name: HostName,
    config_cache: ConfigCache,
    host_label_plugin: PHostLabelDiscoveryPlugin,
) -> None | Parameters | list[Parameters]:
    return _get_plugin_parameters(
        host_name,
        config_cache,
        default_parameters=host_label_plugin.host_label_default_parameters,
        ruleset_name=host_label_plugin.host_label_ruleset_name,
        ruleset_type=host_label_plugin.host_label_ruleset_type,
        rules_getter_function=agent_based_register.get_host_label_ruleset,
    )
