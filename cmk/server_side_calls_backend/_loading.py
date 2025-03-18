#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.discover_plugins import discover_all_plugins, PluginGroup, PluginLocation
from cmk.server_side_calls.v1 import ActiveCheckConfig, entry_point_prefixes, SpecialAgentConfig


def load_active_checks(*, raise_errors: bool) -> Mapping[PluginLocation, ActiveCheckConfig]:
    return discover_all_plugins(
        PluginGroup.SERVER_SIDE_CALLS,
        {ActiveCheckConfig: entry_point_prefixes()[ActiveCheckConfig]},
        raise_errors=raise_errors,
    ).plugins


def load_special_agents(*, raise_errors: bool) -> Mapping[PluginLocation, SpecialAgentConfig]:
    return discover_all_plugins(
        PluginGroup.SERVER_SIDE_CALLS,
        {SpecialAgentConfig: entry_point_prefixes()[SpecialAgentConfig]},
        raise_errors=raise_errors,
    ).plugins
