#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping

from cmk.discover_plugins import discover_all_plugins, PluginGroup, PluginLocation
from cmk.server_side_calls import internal, v1


def load_active_checks(
    *, raise_errors: bool
) -> Mapping[PluginLocation, internal.ActiveCheckConfig | v1.ActiveCheckConfig]:
    entry_points: Mapping[type[internal.ActiveCheckConfig] | type[v1.ActiveCheckConfig], str] = {
        internal.ActiveCheckConfig: internal.entry_point_prefixes()[internal.ActiveCheckConfig],
        v1.ActiveCheckConfig: v1.entry_point_prefixes()[v1.ActiveCheckConfig],
    }
    return discover_all_plugins(
        PluginGroup.SERVER_SIDE_CALLS, entry_points, raise_errors=raise_errors
    ).plugins


def load_special_agents(
    *, raise_errors: bool
) -> Mapping[PluginLocation, internal.SpecialAgentConfig | v1.SpecialAgentConfig]:
    entry_points: Mapping[type[internal.SpecialAgentConfig] | type[v1.SpecialAgentConfig], str] = {
        internal.SpecialAgentConfig: internal.entry_point_prefixes()[internal.SpecialAgentConfig],
        v1.SpecialAgentConfig: v1.entry_point_prefixes()[v1.SpecialAgentConfig],
    }
    return discover_all_plugins(
        PluginGroup.SERVER_SIDE_CALLS, entry_points, raise_errors=raise_errors
    ).plugins
