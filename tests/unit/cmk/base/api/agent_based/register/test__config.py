#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pytest import MonkeyPatch

from cmk.checkengine.checking import CheckPluginName

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.plugin_classes import CheckPlugin

from cmk.discover_plugins import PluginLocation


def test_get_registered_check_plugins(monkeypatch: MonkeyPatch) -> None:
    test_plugin = CheckPlugin(
        CheckPluginName("check_unit_test"),
        [],
        "Unit Test",
        lambda: [],
        None,
        None,
        "merged",
        lambda: [],
        None,
        None,
        None,
        PluginLocation(module="not-relevant"),
    )

    monkeypatch.setattr(
        agent_based_register._config, "registered_check_plugins", {test_plugin.name: test_plugin}
    )

    assert agent_based_register.get_check_plugin(test_plugin.name) is test_plugin
    assert (
        agent_based_register.get_check_plugin(CheckPluginName("mgmt_this_should_not_exists"))
        is None
    )

    mgmt_plugin = agent_based_register.get_check_plugin(
        CheckPluginName("mgmt_%s" % test_plugin.name)
    )
    assert mgmt_plugin is not None
    assert str(mgmt_plugin.name).startswith("mgmt_")
    assert mgmt_plugin.service_name.startswith("Management Interface: ")
