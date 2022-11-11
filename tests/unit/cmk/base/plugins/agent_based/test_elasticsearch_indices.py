#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from tests.testlib import on_time

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import AgentSectionPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    GetRateError,
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult


@pytest.fixture(name="section_plugin", scope="module")
def _section_plugin(fix_register: FixRegister) -> AgentSectionPlugin:
    return fix_register.agent_sections[SectionName("elasticsearch_indices")]


@pytest.fixture(name="check_plugin", scope="module")
def _check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("elasticsearch_indices")]


@pytest.fixture(name="section", scope="module")
def _section(section_plugin: AgentSectionPlugin) -> object:
    return section_plugin.parse_function(
        [
            [".monitoring-kibana-6", "971.0", "765236.0"],
            ["filebeat", "28398.0", "22524354.0"],
            [".monitoring-es-6", "11986.0", "15581765.0"],
        ]
    )


def test_discover(
    check_plugin: CheckPlugin,
    section: object,
) -> None:
    assert list(check_plugin.discovery_function(section)) == [
        Service(item=".monitoring-kibana-6"),
        Service(item="filebeat"),
        Service(item=".monitoring-es-6"),
    ]


@pytest.mark.parametrize(
    ["item", "params", "expected_result"],
    [
        pytest.param(
            "filebeat",
            {},
            [
                Result(state=State.OK, summary="Total count: 28398 docs"),
                Metric("elasticsearch_count", 28398.0),
                Result(state=State.OK, summary="Average count: 30 docs per Minute"),
                Metric("elasticsearch_count_rate", 30.0),
                Result(state=State.OK, summary="Total size: 21.5 MiB"),
                Metric("elasticsearch_size", 22524354.0),
                Result(state=State.OK, summary="Average size: 293 KiB  per Minute"),
                Metric("elasticsearch_size_rate", 300000.0),
            ],
            id="without params",
        ),
        pytest.param(
            "filebeat",
            {
                "elasticsearch_count_rate": (10, 20, 2),
                "elasticsearch_size_rate": (5, 15, 2),
            },
            [
                Result(state=State.OK, summary="Total count: 28398 docs"),
                Metric("elasticsearch_count", 28398.0),
                Result(
                    state=State.CRIT,
                    summary="Average count: 30 docs per Minute (warn/crit at 22 docs per Minute/24 docs per Minute)",
                ),
                Metric(
                    "elasticsearch_count_rate", 30.0, levels=(22.605651338367295, 24.66071055094614)
                ),
                Result(state=State.OK, summary="Total size: 21.5 MiB"),
                Metric("elasticsearch_size", 22524354.0),
                Result(
                    state=State.CRIT,
                    summary="Average size: 293 KiB  per Minute (warn/crit at 211 KiB  per Minute/231 KiB  per Minute)",
                ),
                Metric(
                    "elasticsearch_size_rate",
                    300000.0,
                    levels=(215781.21732077873, 236331.80944656717),
                ),
            ],
            id="with params",
        ),
        pytest.param(
            "missing",
            {},
            [],
            id="missing item",
        ),
    ],
)
def test_check(
    section_plugin: AgentSectionPlugin,
    check_plugin: CheckPlugin,
    section: object,
    item: str,
    params: Mapping[str, object],
    expected_result: CheckResult,
) -> None:
    # temporary workaround to initialize value store
    with on_time(100, "UTC"):
        with pytest.raises(GetRateError):
            list(
                check_plugin.check_function(
                    item="filebeat",
                    params=params,
                    section=section_plugin.parse_function(
                        [
                            ["filebeat", "28298.0", "21524354.0"],
                        ]
                    ),
                )
            )
    with on_time(300, "UTC"):
        assert (
            list(
                check_plugin.check_function(
                    item=item,
                    params=params,
                    section=section,
                )
            )
            == expected_result
        )
