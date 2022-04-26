#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from cmk.utils.type_defs import CheckPluginName

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.checking_classes import CheckPlugin


def test_get_registered_check_plugins(monkeypatch):
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
        None,
    )

    monkeypatch.setattr(
        agent_based_register._config, "registered_check_plugins", {test_plugin.name: test_plugin}
    )

    assert agent_based_register.is_registered_check_plugin(test_plugin.name)
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
