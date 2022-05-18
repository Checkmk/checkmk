#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


@pytest.fixture(scope="session", name="check_plugin")
def check_plugin_from_fix_register(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("sansymphony_pool")]


def test_discover_sansymphony_pool_no_agent_output(check_plugin: CheckPlugin) -> None:
    assert list(check_plugin.discovery_function([])) == []


def test_discover_sansymphony_pool(check_plugin: CheckPlugin) -> None:
    assert list(
        check_plugin.discovery_function(
            [
                [
                    "Disk_pool_1",
                    "57",
                    "Running",
                    "ReadWrite",
                    "Dynamic",
                ]
            ]
        )
    ) == [Service(item="Disk_pool_1")]


def test_check_sansymphony_pool_item_not_found(check_plugin: CheckPlugin) -> None:
    string_table = [
        [
            "Disk_pool_1",
            "57",
            "Running",
            "ReadWrite",
            "Dynamic",
        ]
    ]
    assert (
        list(
            check_plugin.check_function(
                item="Disk_pool_2",
                params={"allocated_pools_percentage_upper": (80.0, 90.0)},
                section=string_table,
            )
        )
        == []
    )


def test_check_sansymphony_pool(check_plugin: CheckPlugin) -> None:
    string_table = [
        [
            "Disk_pool_1",
            "57",
            "Running",
            "ReadWrite",
            "Dynamic",
        ]
    ]
    assert list(
        check_plugin.check_function(
            item="Disk_pool_1",
            params={"allocated_pools_percentage_upper": (80.0, 90.0)},
            section=string_table,
        )
    ) == [
        Result(
            state=State.OK,
            summary="Dynamic pool Disk_pool_1 is running, its cache is in ReadWrite mode",
        ),
        Result(state=State.OK, summary="Pool allocation: 57%"),
        Metric("pool_allocation", 57.0, levels=(80.0, 90.0)),
    ]
