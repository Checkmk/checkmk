#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import AgentSectionPlugin, StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult

_STRING_TABLE = [
    ["[[[/]]]"],
    [
        "***",
        "Report",
        "for",
        "user",
        "quotas",
        "on",
        "device",
        "/dev/mapper/volume-root",
    ],
    ["Block", "grace", "time:", "7days;", "Inode", "grace", "time:", "7days"],
    ["Block", "limits", "File", "limits"],
    ["User", "used", "soft", "hard", "grace", "used", "soft", "hard", "grace"],
    ["----------------------------------------------------------------------"],
    ["root", "--", "6003424", "0", "0", "0", "167394", "0", "0", "0"],
    ["[[[/quarktasche]]]"],
    ["***", "Report", "for", "user", "quotas", "on", "device", "/moo"],
    ["Block", "grace", "time:", "7days;", "Inode", "grace", "time:", "7days"],
    ["Block", "limits", "File", "limits"],
    ["User", "used", "soft", "hard", "grace", "used", "soft", "hard", "grace"],
    ["----------------------------------------------------------------------"],
    ["root", "--", "6003424", "0", "0", "0", "167394", "0", "100000000", "0"],
    ["[[[grp:/nussecke]]]"],
    ["***", "Report", "for", "group", "quotas", "on", "device", "/huiboo"],
    ["Block", "grace", "time:", "7days;", "Inode", "grace", "time:", "7days"],
    ["Block", "limits", "File", "limits"],
    ["User", "used", "soft", "hard", "grace", "used", "soft", "hard", "grace"],
    ["----------------------------------------------------------------------"],
    ["root", "--", "6003424", "0", "0", "0", "167394", "0", "100000000", "0"],
    ["www-data", "--", "4404688", "0", "0", "0", "49314", "31415", "100000000", "0"],
]


@pytest.fixture(name="lnx_quota_plugin")
def fixture_lnx_quota_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("lnx_quota")]


@pytest.fixture(name="lnx_quota_section")
def fixture_lnx_quota_section(fix_register: FixRegister) -> AgentSectionPlugin:
    return fix_register.agent_sections[SectionName("lnx_quota")]


def test_parse(lnx_quota_section: AgentSectionPlugin) -> None:
    assert lnx_quota_section.parse_function(_STRING_TABLE) == {
        "/": {"usr": {"root": [6147506176, 0, 0, 0, 167394, 0, 0, 0]}},
        "/nussecke": {
            "grp": {
                "root": [6147506176, 0, 0, 0, 167394, 0, 100000000, 0],
                "www-data": [4510400512, 0, 0, 0, 49314, 31415, 100000000, 0],
            }
        },
        "/quarktasche": {"usr": {"root": [6147506176, 0, 0, 0, 167394, 0, 100000000, 0]}},
    }


def test_inventory(
    lnx_quota_plugin: CheckPlugin,
    lnx_quota_section: AgentSectionPlugin,
) -> None:
    assert list(
        lnx_quota_plugin.discovery_function(lnx_quota_section.parse_function(_STRING_TABLE))
    ) == [
        Service(item="/", parameters={"user": True, "group": False}),
        Service(item="/quarktasche", parameters={"user": True, "group": False}),
        Service(item="/nussecke", parameters={"user": False, "group": True}),
    ]


@pytest.mark.parametrize(
    "item, params, string_table, expected",
    [
        pytest.param(
            "/",
            {},
            _STRING_TABLE,
            [Result(state=State.OK, summary="All users within quota limits")],
            id="everything ok",
        ),
        pytest.param(
            "/",
            {},
            [
                ["[[[/]]]"],
                [
                    "***",
                    "Report",
                    "for",
                    "user",
                    "quotas",
                    "on",
                    "device",
                    "/dev/mapper/volume-root",
                ],
                ["Block", "grace", "time:", "7days;", "Inode", "grace", "time:", "7days"],
                ["Block", "limits", "File", "limits"],
                ["User", "used", "soft", "hard", "grace", "used", "soft", "hard", "grace"],
                ["----------------------------------------------------------------------"],
                ["root", "--", "6003424", "10", "0", "0", "167394", "0", "0", "0"],
            ],
            [Result(state=State.CRIT, summary="User root exceeded space hard limit 5.73 GiB/0 B")],
            id="quota limits hard reached",
        ),
        pytest.param(
            "/nussecke",
            {"group": True},
            [
                ["[[[grp:/nussecke]]]"],
                ["***", "Report", "for", "group", "quotas", "on", "device", "/huiboo"],
                ["Block", "grace", "time:", "7days;", "Inode", "grace", "time:", "7days"],
                ["Block", "limits", "File", "limits"],
                ["User", "used", "soft", "hard", "grace", "used", "soft", "hard", "grace"],
                ["----------------------------------------------------------------------"],
                ["root", "--", "6003424", "23", "0", "1", "167394", "0", "100000000", "0"],
                ["www-data", "--", "4404688", "0", "0", "0", "49314", "31415", "100000000", "0"],
            ],
            [
                Result(
                    state=State.CRIT, summary="Group root exceeded space hard limit 5.73 GiB/0 B"
                ),
                Result(
                    state=State.WARN, summary="Group www-data exceeded file soft limit 49314/31415"
                ),
            ],
            id="group soft limit and hard limit",
        ),
    ],
)
def test_check(
    lnx_quota_plugin: CheckPlugin,
    lnx_quota_section: AgentSectionPlugin,
    item: str,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected: Sequence[CheckResult],
) -> None:
    assert (
        list(
            lnx_quota_plugin.check_function(
                item=item, params=params, section=lnx_quota_section.parse_function(string_table)
            )
        )
        == expected
    )
