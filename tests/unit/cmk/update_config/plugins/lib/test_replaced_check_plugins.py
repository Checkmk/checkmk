#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkengine.checking import CheckPluginName

from cmk.update_config.plugins.lib.replaced_check_plugins import ALL_REPLACED_CHECK_PLUGINS


def test_ups_eaton_environment_rename_registered() -> None:
    """The misspelled plugin is registered for automatic migration to the corrected name.

    ``cmk-update-config`` uses ``ALL_REPLACED_CHECK_PLUGINS`` (via ``_fix_entry``) to
    rewrite every host's persisted autochecks from the old plugin name to the new one,
    so existing services are migrated without rediscovery.
    """
    assert ALL_REPLACED_CHECK_PLUGINS[CheckPluginName("ups_eaton_enviroment")] == CheckPluginName(
        "ups_eaton_environment"
    )
