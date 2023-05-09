#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

STRING_TABLE: StringTable = [["0.88", "0.83", "0.87", "2/2148", "21050", "8"]]


@pytest.mark.usefixtures("config_load_all_checks")
def test_basic_cpu_loads():
    agent_section = agent_based_register.get_section_plugin(SectionName("cpu"))
    plugin = agent_based_register.get_check_plugin(CheckPluginName("cpu_loads"))
    assert plugin

    section = agent_section.parse_function(STRING_TABLE)  # type: ignore[arg-type]
    result = list(
        plugin.check_function(
            params={"auto-migration-wrapper-key": (5.0, 10.0)},
            section=section,
        ))
    assert result == [
        Result(state=State.OK, summary="15 min load: 0.87 at 8 cores (0.11 per core)"),
        Metric("load1", 0.88, levels=(40.0, 80.0), boundaries=(0.0, 8.0)),
        Metric("load5", 0.83, levels=(40.0, 80.0), boundaries=(0.0, 8.0)),
        Metric("load15", 0.87, levels=(40.0, 80.0), boundaries=(0.0, 8.0)),
    ]
