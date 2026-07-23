#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName
from cmk.gui.watolib.rulesets import RulesetCollection
from cmk.update_config.plugins.lib.autochecks import _fix_entry
from cmk.update_config.plugins.lib.replaced_check_plugins import ALL_REPLACED_CHECK_PLUGINS


def test_ups_eaton_environment_rename_registered() -> None:
    assert ALL_REPLACED_CHECK_PLUGINS[CheckPluginName("ups_eaton_enviroment")] == CheckPluginName(
        "ups_eaton_environment"
    )


def test_fix_entry_migrates_ups_eaton_environment_in_place() -> None:
    """Existing autochecks are migrated to the corrected plugin name without rediscovery.

    ``_fix_entry`` is what ``cmk-update-config`` runs (via ``rewrite_yielding_errors``)
    against every host's persisted autochecks. Here we prove that an entry discovered
    under the misspelled name ``ups_eaton_enviroment`` is rewritten to
    ``ups_eaton_environment`` while keeping the service identity (item) and labels, so
    monitoring continues seamlessly.
    """
    old_entry = AutocheckEntry(
        check_plugin_name=CheckPluginName("ups_eaton_enviroment"),
        item=None,
        parameters={},
        service_labels={"marker": "keep-me"},
    )

    # No registered check plugins / rulesets are needed: the item-less service carries
    # no parameters, so the parameter-migration branch is not entered and
    # ``all_rulesets`` is never accessed.
    fixed = _fix_entry(
        old_entry,
        all_rulesets=cast(RulesetCollection, None),
        check_plugins={},
        hostname="test-host",
    )

    assert fixed.check_plugin_name == CheckPluginName("ups_eaton_environment")
    assert fixed.item is None
    assert fixed.parameters == {}
    assert fixed.service_labels == {"marker": "keep-me"}
