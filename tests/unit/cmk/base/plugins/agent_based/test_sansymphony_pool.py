#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import AgentSectionPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.sansymphony_pool import SansymphonyPool


@pytest.fixture(scope="session", name="check_plugin")
def check_plugin_from_fix_register(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("sansymphony_pool")]


@pytest.fixture(scope="session", name="section_plugin")
def section_plugin_from_fix_register(fix_register: FixRegister) -> AgentSectionPlugin:
    return fix_register.agent_sections[SectionName("sansymphony_pool")]


def test_parse_sansymphony_pool_no_agent_output(section_plugin: AgentSectionPlugin) -> None:
    assert section_plugin.parse_function([]) == {}


def test_parse_sansymphony_pool(section_plugin: AgentSectionPlugin) -> None:
    assert section_plugin.parse_function(
        [
            [
                "Disk_pool_1",
                "57",
                "Running",
                "ReadWrite",
                "Dynamic",
            ]
        ]
    ) == {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            percent_allocated=57.0,
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }


def test_discover_sansymphony_pool_no_agent_output(check_plugin: CheckPlugin) -> None:
    assert list(check_plugin.discovery_function({})) == []


def test_discover_sansymphony_pool(check_plugin: CheckPlugin) -> None:
    assert list(
        check_plugin.discovery_function(
            {
                "Disk_pool_1": SansymphonyPool(
                    name="Disk_pool_1",
                    percent_allocated=57.0,
                    status="Running",
                    cache_mode="ReadWrite",
                    pool_type="Dynamic",
                ),
            }
        )
    ) == [Service(item="Disk_pool_1")]


def test_check_sansymphony_pool_item_not_found(check_plugin: CheckPlugin) -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            percent_allocated=57.0,
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert (
        list(
            check_plugin.check_function(
                item="Disk_pool_2",
                params={"allocated_pools_percentage_upper": (80.0, 90.0)},
                section=section,
            )
        )
        == []
    )


def test_check_sansymphony_pool_status_running_cache_mode_readwrite(
    check_plugin: CheckPlugin,
) -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            percent_allocated=57.0,
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_plugin.check_function(
            item="Disk_pool_1",
            params={"allocated_pools_percentage_upper": (80.0, 90.0)},
            section=section,
        )
    ) == [
        Result(
            state=State.OK,
            summary="Dynamic pool Disk_pool_1 is Running, its cache is in ReadWrite mode",
        ),
        Result(state=State.OK, summary="Pool allocation: 57.00%"),
        Metric("pool_allocation", 57.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]


def test_check_sansymphony_pool_status_running_cache_mode_read(
    check_plugin: CheckPlugin,
) -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            percent_allocated=57.0,
            status="Running",
            cache_mode="Read",  # this is made up
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_plugin.check_function(
            item="Disk_pool_1",
            params={"allocated_pools_percentage_upper": (80.0, 90.0)},
            section=section,
        )
    ) == [
        Result(
            state=State.WARN,
            summary="Dynamic pool Disk_pool_1 is Running, its cache is in Read mode",
        ),
        Result(state=State.OK, summary="Pool allocation: 57.00%"),
        Metric("pool_allocation", 57.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]


def test_check_sansymphony_pool_status_stale(
    check_plugin: CheckPlugin,
) -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            percent_allocated=57.0,
            status="Stale",  # this is made up
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_plugin.check_function(
            item="Disk_pool_1",
            params={"allocated_pools_percentage_upper": (80.0, 90.0)},
            section=section,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Dynamic pool Disk_pool_1 is Stale, its cache is in ReadWrite mode",
        ),
        Result(state=State.OK, summary="Pool allocation: 57.00%"),
        Metric("pool_allocation", 57.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]


def test_check_sansymphony_pool_percent_allocated(
    check_plugin: CheckPlugin,
) -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            percent_allocated=90.0,
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_plugin.check_function(
            item="Disk_pool_1",
            params={"allocated_pools_percentage_upper": (80.0, 90.0)},
            section=section,
        )
    ) == [
        Result(
            state=State.OK,
            summary="Dynamic pool Disk_pool_1 is Running, its cache is in ReadWrite mode",
        ),
        Result(state=State.CRIT, summary="Pool allocation: 90.00% (warn/crit at 80.00%/90.00%)"),
        Metric("pool_allocation", 90.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]
