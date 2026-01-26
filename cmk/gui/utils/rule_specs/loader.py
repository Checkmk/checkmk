#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.version import Edition
from cmk.discover_plugins import (
    discover_all_plugins,
    discover_plugins_from_modules,
    DiscoveredPlugins,
    PluginGroup,
)
from cmk.gui.utils.rule_specs.compatibility import make_rule_spec_backwards_compatible
from cmk.rulesets.v1 import entry_point_prefixes
from cmk.rulesets.v1.rule_specs import (
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


def load_api_v1_rule_specs(
    raise_errors: bool,
) -> tuple[Sequence[Exception], Sequence[LoadedRuleSpec]]:
    discovered_plugins: DiscoveredPlugins[RuleSpec] = discover_all_plugins(
        PluginGroup.RULESETS, entry_point_prefixes(), raise_errors=raise_errors
    )

    # HACK for migrating plugins: also search in certain modules that are not yet moved.
    # This datastructure should only be filled for one commit in a chain, and be emptied
    # right away. This is for convenience of the reviewer of a plugin migration only:
    # This way we can separate migration and moving.
    # For example:

    not_yet_moved_plugins: set[str] = set()
    import cmk.gui.plugins.wato.check_parameters  # astrein: disable=cmk-module-layer-violation

    community_check_parameters_paths = set(cmk.gui.plugins.wato.check_parameters.__path__)
    for community_check_parameters_path in community_check_parameters_paths:
        for plugin in Path(community_check_parameters_path).glob("*.py"):
            if plugin.stem != "__init__":
                not_yet_moved_plugins.add(f"cmk.gui.plugins.wato.check_parameters.{plugin.stem}")

    try:
        import cmk.gui.nonfree.pro.plugins.wato.agent_bakery.rulespecs  # type: ignore[import-not-found, import-untyped, unused-ignore] # astrein: disable=cmk-module-layer-violation

        pro_bakery_ruleset_paths = set(
            cmk.gui.nonfree.pro.plugins.wato.agent_bakery.rulespecs.__path__
        )
        for pro_bakery_ruleset_path in pro_bakery_ruleset_paths:
            for plugin in Path(pro_bakery_ruleset_path).glob("*.py"):
                if plugin.stem != "__init__":
                    not_yet_moved_plugins.add(
                        f"cmk.gui.nonfree.pro.plugins.wato.agent_bakery.rulespecs.{plugin.stem}"
                    )
    except ModuleNotFoundError:
        pass

    try:
        import cmk.gui.nonfree.ultimate.plugins.wato.check_parameters  # type: ignore[import-not-found, import-untyped, unused-ignore] # astrein: disable=cmk-module-layer-violation

        ultimate_check_parameters_paths = set(
            cmk.gui.nonfree.ultimate.plugins.wato.check_parameters.__path__
        )
        for ultimate_check_parameters_path in ultimate_check_parameters_paths:
            for plugin in Path(ultimate_check_parameters_path).glob("*.py"):
                if plugin.stem != "__init__":
                    not_yet_moved_plugins.add(
                        f"cmk.gui.nonfree.ultimate.plugins.wato.check_parameters.{plugin.stem}"
                    )
    except ModuleNotFoundError:
        pass

    if not_yet_moved_plugins:
        more_discovered_plugins = discover_plugins_from_modules(
            entry_point_prefixes(),
            not_yet_moved_plugins,
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
    <Edition.COMMUNITY: _EditionValue(short='community', long='community', title='Checkmk Community (formerly Raw)')>
    >>> _get_edition_only('cmk.plugins.family.rulesets.cce')  # doctest: +SKIP
    <Edition.ULTIMATE: _EditionValue(short='ultimate', long='ultimate', title='Checkmk Ultimate (formerly Cloud)')>
    """
    edition_folder = plugin_module.split(".")[-1]
    for edition in Edition:
        if edition_folder == edition.short:
            return edition
    return Edition.COMMUNITY
