#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cmk.base.configlib.loaded_config import BaseConfig
from cmk.ccc.hostaddress import HostName, Hosts
from cmk.checkengine.inventory import HWSWInventoryParameters
from cmk.checkengine.plugins import InventoryPlugin
from cmk.inventory.structured_data import RawIntervalFromConfig
from cmk.ruleset_matcher.labels import LabelManager
from cmk.ruleset_matcher.matcher import RulesetMatcher


@dataclass(frozen=True)
class InventoryConfig:
    """The host/plugin configuration for the HW/SW inventory."""

    hwsw_parameters: Callable[[HostName], HWSWInventoryParameters]
    plugin_parameters: Callable[[HostName, InventoryPlugin], Mapping[str, object]]
    retention_intervals: Callable[[HostName], Sequence[RawIntervalFromConfig]]
    # Drop the memoized per-host HW/SW parameters. Must be called whenever the
    # inputs (e.g. discovered host labels) may have changed without rebuilding
    # the config, mirroring `ConfigCache.invalidate_host_config`.
    invalidate: Callable[[], None]


def make_inventory_config(
    loaded_config: BaseConfig,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
    hosts_config: Hosts,
) -> InventoryConfig:
    """Create the callbacks that resolve HW/SW inventory configuration per host."""

    def compute_hwsw_parameters(host_name: HostName) -> HWSWInventoryParameters:
        if host_name in hosts_config.clusters:
            return HWSWInventoryParameters.from_raw({})

        # 'get_host_values' is already cached thus we can
        # use it after every check cycle.
        if not (
            entries := matcher.get_host_values_all(
                host_name,
                loaded_config.active_checks.get("cmk_inv") or (),
                label_manager.labels_of_host,
            )
        ):
            return HWSWInventoryParameters.from_raw({})  # No matching rule -> disable

        # Convert legacy rules to current dict format (just like the valuespec)
        # we can only have None or a dict here, but mypy doesn't know that
        return HWSWInventoryParameters.from_raw(entries[0] if isinstance(entries[0], dict) else {})

    hwsw_cache: dict[HostName, HWSWInventoryParameters] = {}

    def hwsw_parameters(host_name: HostName) -> HWSWInventoryParameters:
        with contextlib.suppress(KeyError):
            return hwsw_cache[host_name]
        return hwsw_cache.setdefault(host_name, compute_hwsw_parameters(host_name))

    def plugin_parameters(host_name: HostName, plugin: InventoryPlugin) -> Mapping[str, object]:
        if plugin.ruleset_name is None:
            raise ValueError(plugin)
        return {
            **plugin.defaults,
            **matcher.get_host_values_merged(
                host_name,
                loaded_config.inv_parameters.get(str(plugin.ruleset_name), []),
                label_manager.labels_of_host,
            ),
        }

    def retention_intervals(host_name: HostName) -> Sequence[RawIntervalFromConfig]:
        return [
            raw
            for entry in matcher.get_host_values_all(
                host_name,
                loaded_config.inv_retention_intervals,
                label_manager.labels_of_host,
            )
            for raw in entry
        ]

    return InventoryConfig(
        hwsw_parameters=hwsw_parameters,
        plugin_parameters=plugin_parameters,
        retention_intervals=retention_intervals,
        invalidate=hwsw_cache.clear,
    )
