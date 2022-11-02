#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State


@pytest.fixture
def check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("mssql_instance")]


def test_check_mssql_instance_vanished(
    check_plugin: CheckPlugin,  # pylint: disable=redefined-outer-name
) -> None:
    assert list(check_plugin.check_function(item="MSSQL instance", params={}, section={})) == [
        Result(
            state=State.CRIT, summary="Database or necessary processes not running or login failed"
        ),
    ]
