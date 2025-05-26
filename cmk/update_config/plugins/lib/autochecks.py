#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Generator, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

from cmk.ccc import debug
from cmk.ccc.hostaddress import HostName

from cmk.utils import paths
from cmk.utils.rulesets.definition import RuleGroup

from cmk.checkengine.discovery import AutochecksStore
from cmk.checkengine.legacy import LegacyCheckParameters
from cmk.checkengine.plugin_backend import get_check_plugin
from cmk.checkengine.plugins import AutocheckEntry, CheckPlugin, CheckPluginName

from cmk.base.config import load_all_pluginX

from cmk.gui.watolib.rulesets import AllRulesets, Ruleset, RulesetCollection

from cmk.update_config.plugins.lib.replaced_check_plugins import ALL_REPLACED_CHECK_PLUGINS

TDiscoveredItemsTransforms = Mapping[CheckPluginName, Callable[[str | None], str | None]]

_EXPLICIT_DISCOVERED_ITEMS_TRANSFORMS: TDiscoveredItemsTransforms = {}

_ALL_EXPLICIT_DISCOVERED_ITEMS_TRANSFORMS: TDiscoveredItemsTransforms = {
    **_EXPLICIT_DISCOVERED_ITEMS_TRANSFORMS,
    **{
        name.create_management_name(): transform
        for name, transform in _EXPLICIT_DISCOVERED_ITEMS_TRANSFORMS.items()
    },
}

# some autocheck parameters need transformation even though there is no ruleset.
TDiscoveredParametersTransforms = Mapping[
    CheckPluginName,
    Callable[
        [Any],  # should be LegacyCheckParameters, but this makes writing transforms cumbersome ...
        Mapping[str, object],
    ],
]

_EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS: TDiscoveredParametersTransforms = {
    # cpu_loads no longer discovers any parameters, hence we can just drop them on update
    CheckPluginName("cpu_loads"): lambda x: {},
}

_ALL_EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS: TDiscoveredParametersTransforms = {
    **_EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS,
    **{
        name.create_management_name(): transform
        for name, transform in _EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS.items()
    },
}


@dataclass(frozen=True)
class RewriteError:
    message: str
    host_name: HostName
    plugin: CheckPluginName | None = None


def rewrite_yielding_errors(*, write: bool) -> Iterable[RewriteError]:
    """Rewrite autochecks and yield errors

    This function is used by both the pre- and the regular update_config plug-in,
    to ensure consistency.
    """
    all_rulesets = AllRulesets.load_all_rulesets()
    plugins = load_all_pluginX(paths.checks_dir)
    for hostname in _autocheck_hosts():
        fixed_autochecks = yield from _get_fixed_autochecks(
            hostname, all_rulesets, plugins.check_plugins
        )
        if write:
            AutochecksStore(hostname).write(fixed_autochecks)


def _get_fixed_autochecks(
    host_name: HostName,
    all_rulesets: AllRulesets,
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
) -> Generator[RewriteError, None, list[AutocheckEntry]]:
    try:
        autochecks = AutochecksStore(host_name).read()
    except Exception as exc:
        if debug.enabled():
            raise
        yield RewriteError(message=f"Failed to load autochecks: {exc}", host_name=host_name)
        return []

    fixed_autochecks: list[AutocheckEntry] = []
    for entry in autochecks:
        try:
            fixed_autochecks.append(_fix_entry(entry, all_rulesets, check_plugins, host_name))
        except Exception as exc:
            if debug.enabled():
                raise
            yield RewriteError(
                message=str(exc), host_name=host_name, plugin=entry.check_plugin_name
            )

    return fixed_autochecks


def _autocheck_hosts() -> Iterable[HostName]:
    for autocheck_file in paths.autochecks_dir.glob("*.mk"):
        yield HostName(autocheck_file.stem)


def _fix_entry(
    entry: AutocheckEntry,
    all_rulesets: RulesetCollection,
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
    hostname: str,
) -> AutocheckEntry:
    """Change names of removed plugins to the new ones and transform parameters"""
    new_plugin_name = ALL_REPLACED_CHECK_PLUGINS.get(
        entry.check_plugin_name, entry.check_plugin_name
    )

    explicit_item_transform = _ALL_EXPLICIT_DISCOVERED_ITEMS_TRANSFORMS.get(
        new_plugin_name, lambda x: x
    )
    explicit_parameters_transform = _ALL_EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS.get(
        new_plugin_name, lambda x: x
    )

    return AutocheckEntry(
        check_plugin_name=new_plugin_name,
        item=explicit_item_transform(entry.item),
        parameters=_transformed_params(
            new_plugin_name,
            explicit_parameters_transform(entry.parameters),
            all_rulesets,
            check_plugins,
            hostname,
        ),
        service_labels=entry.service_labels,
    )


T = TypeVar("T", bound=LegacyCheckParameters)


def _transformed_params(
    plugin_name: CheckPluginName,
    params: T,
    all_rulesets: RulesetCollection,
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
    host: str,
) -> Mapping[str, object]:
    if (ruleset := _get_ruleset(plugin_name, all_rulesets, check_plugins)) is None:
        if not params:
            return {}
        if isinstance(params, dict):
            return {str(k): v for k, v in params.items()}
        raise TypeError(
            f"Migration missing: {params=} for plug-in '{str(plugin_name)}' (expected type dict)"
        )

    try:
        new_params = _apply_rulesets_migration(params, ruleset, plugin_name)
        assert new_params or not params, "non-empty params vanished"
    except Exception as exc:
        raise ValueError(
            f"Migration failed: {params=} for plug-in '{str(plugin_name)}': {exc}"
        ) from exc

    return new_params


def _get_ruleset(
    plugin_name: CheckPluginName,
    all_rulesets: RulesetCollection,
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
) -> Ruleset | None:
    if (
        check_plugin := get_check_plugin(plugin_name, check_plugins)
    ) is None or check_plugin.check_ruleset_name is None:
        return None

    return all_rulesets.get_rulesets().get(
        RuleGroup.CheckgroupParameters(f"{check_plugin.check_ruleset_name}")
    )


def _apply_rulesets_migration(
    params: LegacyCheckParameters, ruleset: Ruleset, plugin_name: CheckPluginName
) -> Mapping[str, object]:
    new_params = ruleset.valuespec().transform_value(params) if params else {}

    if not (isinstance(new_params, dict) and all(isinstance(k, str) for k in new_params)):
        raise TypeError(
            f"Migration invalid: {new_params=} for '{str(plugin_name)}' (expected type dict)"
        )

    return new_params
