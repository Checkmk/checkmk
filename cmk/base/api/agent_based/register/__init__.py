#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.debug
import cmk.utils.paths

from cmk.utils.log import console
from cmk.utils.plugin_loader import load_plugins_with_exceptions

from cmk.base.api.agent_based.register._config import (
    add_check_plugin,
    add_discovery_ruleset,
    add_inventory_plugin,
    add_section_plugin,
    get_check_plugin,
    get_discovery_ruleset,
    get_inventory_plugin,
    get_relevant_raw_sections,
    get_ranked_sections,
    get_section_plugin,
    is_registered_check_plugin,
    is_registered_inventory_plugin,
    is_registered_section_plugin,
    iter_all_agent_sections,
    iter_all_check_plugins,
    iter_all_discovery_rulesets,
    iter_all_inventory_plugins,
    iter_all_snmp_sections,
    set_discovery_ruleset,
)


def load_all_plugins():
    for plugin, exception in load_plugins_with_exceptions("cmk.base.plugins.agent_based"):
        console.error("Error in agent based plugin %s: %s\n", plugin, exception)
        if cmk.utils.debug.enabled():
            raise exception


__all__ = [
    "add_check_plugin",
    "add_discovery_ruleset",
    "add_inventory_plugin",
    "add_section_plugin",
    "get_check_plugin",
    "get_discovery_ruleset",
    "get_inventory_plugin",
    "get_relevant_raw_sections",
    "get_ranked_sections",
    "get_section_plugin",
    "is_registered_check_plugin",
    "is_registered_inventory_plugin",
    "is_registered_section_plugin",
    "iter_all_agent_sections",
    "iter_all_check_plugins",
    "iter_all_discovery_rulesets",
    "iter_all_inventory_plugins",
    "iter_all_snmp_sections",
    "load_all_plugins",
    "set_discovery_ruleset",
]
