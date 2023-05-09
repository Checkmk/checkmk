#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State


@pytest.mark.usefixtures("config_load_all_checks")
def test_make_sure_bluecat_threads_can_handle_new_params_format() -> None:
    plugin = agent_based_register.get_check_plugin(CheckPluginName("bluecat_threads"))
    assert plugin
    assert list(plugin.check_function(
        params={"levels": ("levels", (10, 20))},
        section=[["1234"]],
    )) == [
        Result(state=State.CRIT, summary="1234 threads (critical at 20)"),
        Metric("threads", 1234.0, levels=(10.0, 20.0), boundaries=(0.0, None)),
    ]
