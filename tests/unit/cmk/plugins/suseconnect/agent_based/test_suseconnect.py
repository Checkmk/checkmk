#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Callable
from typing import Final
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Attributes, CheckResult, DiscoveryResult, Result, Service, State
from cmk.checkengine.plugins import CheckPluginName
from cmk.plugins.suseconnect.agent_based.agent_section import parse, Section
from cmk.plugins.suseconnect.agent_based.inventory import inventory


@pytest.fixture(name="plugin", scope="module")
def _get_plugin(agent_based_plugins):
    return agent_based_plugins.check_plugins[CheckPluginName("suseconnect")]


@pytest.fixture(name="discover_suseconnect", scope="module")
def _get_disvovery_function(plugin):
    return lambda section: plugin.discovery_function(section=section)


@pytest.fixture(name="check_suseconnect", scope="module")
def _get_check_function(plugin):
    return lambda params, section: plugin.check_function(params=params, section=section)


STRING_TABLE_1: Final = [
    ["identifier", " SLES"],
    ["version", " 12.1"],
    ["arch", " x86_64"],
    ["status", " Registered"],
    ["regcode", " banana001"],
    ["starts_at", " 2015-12-01 00", "00", "00 UTC"],
    ["expires_at", " 2019-12-31 00", "00", "00 UTC"],
    ["subscription_status", " ACTIVE"],
    ["type", " full"],
]


@pytest.fixture(name="section_1", scope="module")
def _get_section_1() -> Section:
    return parse(STRING_TABLE_1)


def test_discovery(
    discover_suseconnect: Callable[[Section], DiscoveryResult], section_1: Section
) -> None:
    assert list(discover_suseconnect(section_1)) == [Service()]


def test_check(
    check_suseconnect: Callable[[object, Section], CheckResult], section_1: Section
) -> None:
    with time_machine.travel(datetime.datetime(2020, 7, 15, tzinfo=ZoneInfo("UTC"))):
        assert list(
            check_suseconnect(
                {"status": "Registered", "subscription_status": "ACTIVE", "days_left": (14, 7)},
                section_1,
            )
        ) == [
            Result(state=State.OK, summary="Status: Registered"),
            Result(state=State.OK, summary="Subscription: ACTIVE"),
            Result(
                state=State.OK,
                summary=(
                    "Subscription type: full, Registration code: banana001, "
                    "Starts at: 2015-12-01 00:00:00 UTC, "
                    "Expires at: 2019-12-31 00:00:00 UTC"
                ),
            ),
            Result(state=State.CRIT, summary="Expired since: 197 days 0 hours"),
        ]


def test_agent_output_parsable(
    check_suseconnect: Callable[[object, Section], DiscoveryResult],
) -> None:
    with time_machine.travel(datetime.datetime(2020, 7, 15, tzinfo=ZoneInfo("UTC"))):
        assert list(
            check_suseconnect(
                {
                    "status": "Registered",
                    "subscription_status": "ACTIVE",
                    "days_left": ("fixed", (14.0, 7.0)),
                },
                parse(
                    [
                        ["Installed Products", ""],
                        ["Advanced Systems Management Module"],
                        ["(sle-module-adv-systems-management/12/x86_64)"],
                        ["Registered"],
                        ["SUSE Linux Enterprise Server for SAP Applications 12 SP5"],
                        ["(SLES_SAP/12.5/x86_64)"],
                        ["Registered"],
                        ["Subscription", ""],
                        ["Regcode", " banana005"],
                        ["Starts at", " 2018-07-01 00", "00", "00 UTC"],
                        ["Expires at", " 2021-06-30 00", "00", "00 UTC"],
                        ["Status", " ACTIVE"],
                        ["Type", " full"],
                        ["SUSE Package Hub 12"],
                        ["(PackageHub/12.5/x86_64)"],
                        ["Registered"],
                    ]
                ),
            )
        )


def test_inventory(section_1: Section) -> None:
    assert list(inventory(section_1)) == [
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "License Begin": "2015-12-01 00:00:00 UTC",
                "License Expiration": "2019-12-31 00:00:00 UTC",
                "Subscription Status": "ACTIVE",
            },
        ),
    ]
