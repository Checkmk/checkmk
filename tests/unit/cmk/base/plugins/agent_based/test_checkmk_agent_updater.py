#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State


@pytest.fixture(name="fix_time")
def _get_fix_time():
    with on_time(1645800081.5039608, "UTC"):
        yield


@pytest.fixture(scope="module", name="plugin")
def _get_plugin(fix_register):
    return fix_register.check_plugins[CheckPluginName("check_mk_agent_update")]


@pytest.fixture(scope="module", name="discover_cmk_agent_update")
def _get_discovery_function(plugin):
    return lambda s: plugin.discovery_function(section=s)


@pytest.fixture(scope="module", name="check_cmk_agent_update")
def _get_check_function(plugin):
    return lambda p, s: plugin.check_function(params=p, section=s)


def test_discovery_nothing(discover_cmk_agent_update) -> None:
    assert not [*discover_cmk_agent_update({})]


def test_discovery_something(discover_cmk_agent_update) -> None:
    assert [*discover_cmk_agent_update({"agentupdate": "something"})] == [Service()]


def test_check_no_data(check_cmk_agent_update) -> None:
    assert not [*check_cmk_agent_update({}, {})]


def test_check_no_check_yet(check_cmk_agent_update) -> None:
    assert [*check_cmk_agent_update({}, {"agentupdate": "last_check None error None"})] == [
        Result(state=State.WARN, summary="No successful connect to server yet"),
    ]


@pytest.mark.parametrize("duplicate", [False, True])
def test_check_warn_upon_old_update_check(
    fix_time, duplicate: bool, check_cmk_agent_update
) -> None:
    assert [
        *check_cmk_agent_update(
            {},
            {
                "agentupdate": " ".join(
                    (1 + duplicate)
                    * (
                        "last_check 1645000081.5039608",
                        "last_update 1645000181.5039608",
                        "aghash 38bf6e44175732bc",
                        "pending_hash 1234abcd5678efgh",
                        "update_url https://server/site/check_mk",
                        "error 503 Server Error: Service Unavailable",
                    )
                )
            },
        )
    ] == [
        Result(state=State.WARN, summary="Error: 503 Server Error: Service Unavailable"),
        Result(
            state=State.WARN, summary="Time since last update check: 9 d (warn/crit at 2 d/never)"
        ),
        Result(state=State.OK, summary="Last update check: 2022-02-16 08:28:01"),
        Result(state=State.OK, summary="Last agent update: 2022-02-16 08:29:41"),
        Result(state=State.OK, summary="Update URL: https://server/site/check_mk"),
        Result(state=State.OK, summary="Agent configuration: 38bf6e44"),
        Result(state=State.OK, summary="Pending installation: 1234abcd"),
    ]
