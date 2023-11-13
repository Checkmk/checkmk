#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import cmk.utils.debug

from cmk.discover_plugins import discover_plugins
from cmk.server_side_calls.v1 import ActiveCheckConfig, SpecialAgentConfig


def load_active_checks() -> tuple[Sequence[str], Mapping[str, ActiveCheckConfig]]:
    loaded = discover_plugins(
        "server_side_calls",
        "active_check_",
        ActiveCheckConfig,
        raise_errors=cmk.utils.debug.enabled(),
    )
    # TODO:
    #  * see if we really need to return the errors. Maybe we can just either ignore or raise them.
    #  * deal with duplicate names.
    return [str(e) for e in loaded.errors], {
        plugin.name: plugin for plugin in loaded.plugins.values()
    }


def load_special_agents() -> tuple[Sequence[str], Mapping[str, SpecialAgentConfig]]:
    loaded = discover_plugins(
        "server_side_calls",
        "special_agent_",
        SpecialAgentConfig,
        raise_errors=cmk.utils.debug.enabled(),
    )
    # TODO:
    #  * see if we really need to return the errors. Maybe we can just either ignore or raise them.
    #  * deal with duplicate names.
    return [str(e) for e in loaded.errors], {
        plugin.name: plugin for plugin in loaded.plugins.values()
    }
