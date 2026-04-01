#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import importlib
import pkgutil
from collections.abc import Sequence
from dataclasses import dataclass

from cmk.ccc.version import Edition
from cmk.discover_plugins import (
    discover_all_plugins,
    discover_plugins_from_modules,
    DiscoveredPlugins,
    PluginGroup,
)
from cmk.gui.rule_specs.compatibility import make_rule_spec_backwards_compatible
from cmk.rulesets.v1 import entry_point_prefixes
from cmk.rulesets.v1.rule_specs import (
    AgentConfig,
    CheckParameters,
    EnforcedService,
)

from .types import RuleSpec


@dataclass(frozen=True)
class LoadedRuleSpec:
    rule_spec: RuleSpec
    edition_only: Edition


def load_discovered_rule_specs(
    discovered_plugins: DiscoveredPlugins[RuleSpec],
) -> tuple[Sequence[Exception], Sequence[LoadedRuleSpec]]:
    loaded_plugins = [
        LoadedRuleSpec(
            rule_spec=make_rule_spec_backwards_compatible(plugin),
            edition_only=_get_edition_only(location.module),
        )
        for location, plugin in discovered_plugins.plugins.items()
    ]
    loaded = [
        *loaded_plugins,
        *generate_additional_plugins(discovered_plugins),
    ]
    # TODO:
    #  * see if we really need to return the errors. Maybe we can just either ignore or raise them.
    return discovered_plugins.errors, loaded


def _discover_modules_from(*names: str) -> set[str]:
    return {
        m.name
        for name in names
        for m in pkgutil.iter_modules(importlib.import_module(name).__path__, f"{name}.")
    }


def load_api_v1_rule_specs(
    raise_errors: bool,
    edition: Edition,
) -> tuple[Sequence[Exception], Sequence[LoadedRuleSpec]]:
    used_entry_points = (
        {
            type_: prefix
            for type_, prefix in entry_point_prefixes().items()
            if type_ is not AgentConfig
        }
        if edition is Edition.COMMUNITY
        else entry_point_prefixes()
    )

    discovered_plugins: DiscoveredPlugins[RuleSpec] = discover_all_plugins(
        PluginGroup.RULESETS,
        used_entry_points,
        skip_wrong_types=True,
        raise_errors=raise_errors,
    )

    # HACK for migrating plugins: also search in certain modules that are not yet moved.
    # This is for convenience of the reviewer of a plugin migration only:
    # This way we can separate migration and moving.
    not_yet_moved_plugins = set[str]()
    match edition:
        case Edition.COMMUNITY:
            not_yet_moved_plugins = _discover_modules_from(
                "cmk.gui.plugins.wato.check_parameters",
            )
        case Edition.PRO:
            not_yet_moved_plugins = _discover_modules_from(
                "cmk.gui.plugins.wato.check_parameters",
                "cmk.gui.nonfree.pro.plugins.wato.agent_bakery.rulespecs",
            )
        case Edition.ULTIMATE | Edition.ULTIMATEMT | Edition.CLOUD:
            not_yet_moved_plugins = _discover_modules_from(
                "cmk.gui.plugins.wato.check_parameters",
                "cmk.gui.nonfree.pro.plugins.wato.agent_bakery.rulespecs",
                "cmk.gui.nonfree.ultimate.plugins.wato.check_parameters",
            )

    if not_yet_moved_plugins:
        more_discovered_plugins = discover_plugins_from_modules(
            entry_point_prefixes(),
            not_yet_moved_plugins,
            skip_wrong_types=False,
            raise_errors=raise_errors,
        )
        discovered_plugins = DiscoveredPlugins(
            [*discovered_plugins.errors, *more_discovered_plugins.errors],
            {**discovered_plugins.plugins, **more_discovered_plugins.plugins},
        )

    return load_discovered_rule_specs(discovered_plugins)


def generate_additional_plugins(
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
    <Edition.COMMUNITY: _EditionValue(short='community', long='community', title='Checkmk Community')>
    >>> _get_edition_only('cmk.plugins.family.rulesets.cce')  # doctest: +SKIP
    <Edition.ULTIMATE: _EditionValue(short='ultimate', long='ultimate', title='Checkmk Ultimate')>
    """
    edition_folder = plugin_module.rsplit(".", maxsplit=1)[-1]
    for edition in Edition:
        if edition_folder == edition.short:
            return edition
    return Edition.COMMUNITY
