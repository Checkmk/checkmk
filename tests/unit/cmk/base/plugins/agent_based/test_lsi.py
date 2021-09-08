#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.lsi import parse_lsi

INFO = [
    ["VolumeID", "286"],
    ["Statusofvolume", "Okay(OKY)"],
    ["TargetID", "15"],
    ["State", "Optimal(OPT)"],
    ["TargetID", "1"],
    ["State", "Optimal(OPT)"],
]


def test_lsi_parsing(fix_register):
    result = parse_lsi(INFO)
    assert "disks" in result and "arrays" in result
    assert "286" in result["arrays"]
    assert "1" in result["disks"]
    assert result["disks"]["1"] == "OPT"


@pytest.mark.parametrize(
    "plugin,expected",
    [
        (
            "lsi_array",
            [
                Service(item="286"),
            ],
        ),
        (
            "lsi_disk",
            [
                Service(item="15", parameters={"expected_state": "OPT"}),
                Service(item="1", parameters={"expected_state": "OPT"}),
            ],
        ),
    ],
)
def test_lsi_discovery(fix_register, plugin, expected):
    plugin = fix_register.check_plugins[CheckPluginName(plugin)]
    section = parse_lsi(INFO)
    assert list(plugin.discovery_function(section=section)) == expected


def test_lsi_array(fix_register):
    plugin = fix_register.check_plugins[CheckPluginName("lsi_array")]
    section = parse_lsi(INFO)
    assert list(plugin.check_function(item="286", params={}, section=section)) == [
        Result(state=State.OK, summary="Status is 'Okay(OKY)'")
    ]


@pytest.mark.parametrize(
    "plugin,item,params,expected",
    [
        (
            "lsi_disk",
            "1",
            {"expected_state": "OPT"},
            [Result(state=State.OK, summary="Disk has state 'OPT'")],
        ),
        (
            "lsi_disk",
            "15",
            {"expected_state": "OPT"},
            [Result(state=State.OK, summary="Disk has state 'OPT'")],
        ),
    ],
)
def test_lsi(fix_register, plugin, item, params, expected):
    plugin = fix_register.check_plugins[CheckPluginName(plugin)]
    section = parse_lsi(INFO)
    assert (
        list(
            plugin.check_function(
                item=item,
                params=params,
                section=section,
            )
        )
        == expected
    )
