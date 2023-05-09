#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import SectionPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

STRING_TABLE_RELATIVE: StringTable = [
    # agent output contains the maximum number of threads
    # so we can also check for thread usage
    ["0.88", "0.83", "0.87", "2/1748", "21050", "8"],
    ["124069"],
]

STRING_TABLE: StringTable = [["0.88", "0.83", "0.87", "2/2148", "21050", "8"]]


@pytest.fixture(name="plugin")
def fixture_plugin(config_load_all_checks):
    plugin = agent_based_register.get_check_plugin(CheckPluginName("cpu_threads"))
    assert plugin
    return plugin


@pytest.fixture(name="agent_section")
def fixture_agent_section(config_load_all_checks):
    agent_section = agent_based_register.get_section_plugin(SectionName("cpu"))
    return agent_section


def test_basic_cpu_threads_with_absolute_count(
    plugin: CheckPlugin,
    agent_section: SectionPlugin,
) -> None:
    section = agent_section.parse_function(STRING_TABLE_RELATIVE)  # type: ignore[arg-type]
    assert list(plugin.check_function(params={}, section=section)) == [
        Result(state=State.OK, summary="Count: 1748 threads"),
        Metric("threads", 1748.0),
        Result(state=State.OK, summary="Usage: 1.41%"),
        Metric("thread_usage", 1.408893438328672),
    ]


def test_basic_cpu_threads_without_absolute_count(
    plugin: CheckPlugin,
    agent_section: SectionPlugin,
) -> None:
    section = agent_section.parse_function(STRING_TABLE)  # type: ignore[arg-type]
    assert list(plugin.check_function(params={}, section=section)) == [
        Result(state=State.OK, summary="Count: 2148 threads"),
        Metric("threads", 2148.0),
    ]


@pytest.mark.parametrize(
    "params, levels",
    [
        pytest.param(
            {},
            {
                "thread_usage": (None, None),
                "threads": (None, None)
            },
            id="implicitly no levels set",
        ),
        pytest.param(
            {"levels_percent": "no_levels"},
            {
                "thread_usage": (None, None),
                "threads": (None, None)
            },
            id="explicitly unset levels_percent",
        ),
        pytest.param(
            {"levels_percent": ("levels", (10, 20))},
            {
                "thread_usage": (10, 20),
                "threads": (None, None)
            },
            id="levels set",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_relative_but_no_absolute_levels(
    params,
    levels,
    plugin: CheckPlugin,
    agent_section: SectionPlugin,
):
    section = agent_section.parse_function(STRING_TABLE_RELATIVE)  # type: ignore[arg-type]
    found_levels = {}
    for element in plugin.check_function(params=params, section=section):
        if isinstance(element, Metric):
            found_levels[element.name] = element.levels
    assert found_levels == levels
