#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.plugin_classes import AgentBasedPlugins, CheckPlugin

from cmk.agent_based.v2 import Result, State


@pytest.fixture
def check_plugin(agent_based_plugins: AgentBasedPlugins) -> CheckPlugin:
    return agent_based_plugins.check_plugins[CheckPluginName("mssql_instance")]


def test_check_mssql_instance_vanished(
    check_plugin: CheckPlugin,
) -> None:
    assert list(check_plugin.check_function(item="MSSQL instance", params={}, section={})) == [
        Result(
            state=State.CRIT, summary="Database or necessary processes not running or login failed"
        ),
    ]
