#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.mrpe import check_mrpe, discover_mrpe, parse_mrpe, PluginData

SECTION: Final = {
    "Bar_Extender": PluginData(
        name=None,
        state=State.WARN,
        info=["Bar extender overload 6.012|bar_load=6.012"],
        cache_info=None,
    ),
    "Foo_Application": PluginData(
        name=None, state=State.OK, info=["Foo server up and running"], cache_info=None
    ),
    "Mutliliner": PluginData(
        name=None,
        state=State.UNKNOWN,
        info=[
            "Invalid plugin status '§$%'. Output is: Output1|the_foo=1;2;3;4;5",
            "more output|the_bar=42",
            "the_gee=23 output|the_bad=U;0;;0;1",
        ],
        cache_info=None,
    ),
    "Invalid_Metric": PluginData(
        name=None,
        state=State.OK,
        info=["I would be ok, if it wasn't for the metric|broken="],
        cache_info=None,
    ),
}


def test_parsing() -> None:
    assert SECTION == parse_mrpe(
        [
            ["Foo_Application", "0", "Foo", "server", "up", "and", "running"],
            [
                "Bar_Extender",
                "1",
                "Bar",
                "extender",
                "overload",
                "6.012|bar_load=6.012",
            ],
            [
                "Mutliliner",
                "§$%",
                "Output1|the_foo=1;2;3;4;5\x01more",
                "output|the_bar=42\x01the_gee=23",
                "output|the_bad=U;0;;0;1",
            ],
            [
                "Invalid_Metric",
                "0",
                "I",
                "would",
                "be",
                "ok,",
                "if",
                "it",
                "wasn't",
                "for",
                "the",
                "metric|broken=",
            ],
        ]
    )


def test_discovery() -> None:
    assert list(discover_mrpe(SECTION)) == [
        Service(item="Bar_Extender"),
        Service(item="Foo_Application"),
        Service(item="Mutliliner"),
        Service(item="Invalid_Metric"),
    ]


def test_check_mrpe() -> None:
    assert list(check_mrpe("Bar_Extender", SECTION)) == [
        Result(
            state=State.WARN,
            summary="Bar extender overload 6.012",
        ),
        Metric("bar_load", 6.012),
    ]

    assert list(check_mrpe("Foo_Application", SECTION)) == [
        Result(
            state=State.OK,
            summary="Foo server up and running",
        ),
    ]

    assert list(check_mrpe("Mutliliner", SECTION)) == [
        Result(
            state=State.UNKNOWN,
            summary="Invalid plugin status '§$%'. Output is: Output1",
            details="Invalid plugin status '§$%'. Output is: Output1\nmore output",
        ),
        Metric("the_foo", 1, levels=(2, 3), boundaries=(4, 5)),
        Metric("the_bar", 42),
        Metric("the_gee", 23),
        Result(
            state=State.UNKNOWN,
            summary="Undefined metric: Nagios style undefined value",
        ),
    ]


def test_check_invalid_metric() -> None:
    assert list(check_mrpe("Invalid_Metric", SECTION)) == [
        Result(
            state=State.OK,
            summary="I would be ok, if it wasn't for the metric",
        ),
        Result(
            state=State.UNKNOWN,
            summary="Undefined metric: invalid metric value ''",
        ),
    ]
