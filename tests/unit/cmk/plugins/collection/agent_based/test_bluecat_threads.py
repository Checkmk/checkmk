#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.unit.conftest import FixRegister

from cmk.checkengine.checking import CheckPluginName

from cmk.agent_based.v2 import Metric, Result, State


def test_make_sure_bluecat_threads_can_handle_new_params_format(
    fix_register: FixRegister,
) -> None:
    plugin = fix_register.check_plugins[CheckPluginName("bluecat_threads")]
    assert plugin
    assert list(
        plugin.check_function(
            params={"levels": ("levels", (10, 20))},
            section=[["1234"]],
        )
    ) == [
        Result(state=State.CRIT, summary="1234 threads (critical at 20)"),
        Metric("threads", 1234.0, levels=(10.0, 20.0), boundaries=(0.0, None)),
    ]
