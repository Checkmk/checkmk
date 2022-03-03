#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.checkmk_agent import check_checkmk_agent, discover_checkmk_agent


@pytest.fixture(name="fix_time")
def _get_fix_time():
    with on_time(1645800081.5039608, "UTC"):
        yield


def test_discovery_something() -> None:
    assert [*discover_checkmk_agent({}, None)] == [Service()]


def test_check_no_data() -> None:
    assert not [*check_checkmk_agent({}, {}, None)]


def test_check_no_check_yet() -> None:
    assert [*check_checkmk_agent({}, {"agentupdate": "last_check None error None"}, None)] == [
        Result(state=State.WARN, summary="No successful connect to server yet"),
    ]


@pytest.mark.parametrize("duplicate", [False, True])
def test_check_warn_upon_old_update_check(fix_time, duplicate: bool) -> None:
    assert [
        *check_checkmk_agent(
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
            None,
        )
    ] == [
        Result(state=State.WARN, summary="Error: 503 Server Error: Service Unavailable"),
        Result(
            state=State.WARN,
            summary="Time since last update check: 9 days 6 hours (warn/crit at 2 days 0 hours/never)",
        ),
        Result(state=State.OK, summary="Last update check: Feb 16 2022 08:28:01"),
        Result(state=State.OK, summary="Last agent update: Feb 16 2022 08:29:41"),
        Result(state=State.OK, summary="Update URL: https://server/site/check_mk"),
        Result(state=State.OK, summary="Agent configuration: 38bf6e44"),
        Result(state=State.OK, summary="Pending installation: 1234abcd"),
    ]
