#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.discover_plugins import discover_all_plugins, PluginGroup, PluginLocation
from cmk.server_side_calls import alpha, v1


def load_active_checks(
    *, raise_errors: bool
) -> Mapping[PluginLocation, alpha.ActiveCheckConfig | v1.ActiveCheckConfig]:
    entry_points: Mapping[type[alpha.ActiveCheckConfig] | type[v1.ActiveCheckConfig], str] = {
        alpha.ActiveCheckConfig: alpha.entry_point_prefixes()[alpha.ActiveCheckConfig],
        v1.ActiveCheckConfig: v1.entry_point_prefixes()[v1.ActiveCheckConfig],
    }
    return discover_all_plugins(
        PluginGroup.SERVER_SIDE_CALLS, entry_points, raise_errors=raise_errors
    ).plugins


def load_special_agents(
    *, raise_errors: bool
) -> Mapping[PluginLocation, alpha.SpecialAgentConfig | v1.SpecialAgentConfig]:
    entry_points: Mapping[type[alpha.SpecialAgentConfig] | type[v1.SpecialAgentConfig], str] = {
        alpha.SpecialAgentConfig: alpha.entry_point_prefixes()[alpha.SpecialAgentConfig],
        v1.SpecialAgentConfig: v1.entry_point_prefixes()[v1.SpecialAgentConfig],
    }
    return discover_all_plugins(
        PluginGroup.SERVER_SIDE_CALLS, entry_points, raise_errors=raise_errors
    ).plugins
