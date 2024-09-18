#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import cmk.ccc.debug

from cmk.discover_plugins import discover_plugins, PluginGroup, PluginLocation
from cmk.server_side_calls.v1 import ActiveCheckConfig, entry_point_prefixes, SpecialAgentConfig


def load_active_checks() -> tuple[Sequence[str], Mapping[PluginLocation, ActiveCheckConfig]]:
    loaded = discover_plugins(
        PluginGroup.SERVER_SIDE_CALLS,
        {ActiveCheckConfig: entry_point_prefixes()[ActiveCheckConfig]},
        raise_errors=cmk.ccc.debug.enabled(),
    )
    # TODO:
    #  * see if we really need to return the errors. Maybe we can just either ignore or raise them.
    return [str(e) for e in loaded.errors], loaded.plugins


def load_special_agents() -> tuple[Sequence[str], Mapping[PluginLocation, SpecialAgentConfig]]:
    loaded = discover_plugins(
        PluginGroup.SERVER_SIDE_CALLS,
        {SpecialAgentConfig: entry_point_prefixes()[SpecialAgentConfig]},
        raise_errors=cmk.ccc.debug.enabled(),
    )
    # TODO:
    #  * see if we really need to return the errors. Maybe we can just either ignore or raise them.
    return [str(e) for e in loaded.errors], loaded.plugins
