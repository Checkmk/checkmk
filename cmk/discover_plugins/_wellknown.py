#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This bundles the paths or names that are of special significance for plug-in loading"""

import enum

CMK_PLUGINS = "cmk.plugins"
CMK_ADDONS_PLUGINS = "cmk_addons.plugins"

LIBEXEC_FOLDER = "libexec"


class PluginGroup(enum.Enum):
    """Definitive list of discoverable plug-in groups"""

    AGENT_BASED = "agent_based"
    CHECKMAN = "checkman"
    GRAPHING = "graphing"
    RULESETS = "rulesets"
    SERVER_SIDE_CALLS = "server_side_calls"
