#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.discover_plugins import discover_families, PluginGroup
from cmk.server_side_calls_backend import load_active_checks
from cmk.utils import man_pages


def test_man_page_consistency(agent_based_plugins: AgentBasedPlugins) -> None:
    """Make sure we have one man page per plugin, and no additional ones"""
    man_page_names = set(
        man_pages.make_man_page_path_map(
            discover_families(raise_errors=True), PluginGroup.CHECKMAN.value
        )
    )
    expected_man_pages = (
        {str(plugin_name) for plugin_name in agent_based_plugins.check_plugins}
        | {f"check_{plugin.name}" for plugin in load_active_checks(raise_errors=False).values()}
        | {"check-mk", "check-mk-inventory"}
    )
    missing_manpages = expected_man_pages - man_page_names
    assert not missing_manpages
    unexpected_manpages = man_page_names - expected_man_pages
    assert not unexpected_manpages
