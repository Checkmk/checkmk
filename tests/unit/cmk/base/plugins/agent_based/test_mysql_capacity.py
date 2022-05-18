#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Callable

import pytest

from cmk.utils.type_defs.pluginname import CheckPluginName

import cmk.base.plugin_contexts
from cmk.base.api.agent_based.checking_classes import Metric, Result, Service, State


@pytest.fixture(name="check")
def _check(fix_register) -> Callable:
    return fix_register.check_plugins[CheckPluginName("mysql_capacity")].check_function


@pytest.fixture(name="discovery")
def _discovery(fix_register) -> Callable:
    return fix_register.check_plugins[CheckPluginName("mysql_capacity")].discovery_function


def test_discovery(discovery):
    section = {
        "mysql": {
            "red": (12, 0),
            "information_schema": (12, 0),
            "performance_schema": (12, 0),
            "mysql": (12, 0),
        }
    }
    assert list(discovery(section)) == [Service(item="mysql:red")]


def test_check(check):
    item = "mysql:reddb"
    params = {"auto-migration-wrapper-key": (None, None)}
    section = {"mysql": {"reddb": (42, 0)}}
    with cmk.base.plugin_contexts.current_host("my_host"):
        assert list(check(item=item, params=params, section=section)) == [
            Result(state=State.OK, summary="Size: 42.00 B"),
            Metric("database_size", 42.0),
        ]
