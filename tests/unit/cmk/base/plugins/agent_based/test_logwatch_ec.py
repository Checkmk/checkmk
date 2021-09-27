#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import logwatch_ec
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.logwatch_section import parse_logwatch

INFO1 = [
    ["[[[log1]]]"],
    ["[[[log2]]]"],
    ["[[[log3:missing]]]"],
    ["[[[log4:cannotopen]]]"],
    ["[[[log5]]]"],
    ["[[[log1:missing]]]"],
]

INFO2 = [
    ["[[[log2]]]"],
    ["[[[log3:missing]]]"],
    ["[[[log4:cannotopen]]]"],
    ["[[[log5]]]"],
]


@pytest.mark.parametrize(
    "info, fwd_rule, expected_result",
    [
        (INFO1, [], []),
        (
            INFO1,
            [{"separate_checks": True}],
            [
                Service(item="log1", parameters={"expected_logfiles": ["log1"]}),
                Service(item="log2", parameters={"expected_logfiles": ["log2"]}),
                Service(item="log5", parameters={"expected_logfiles": ["log5"]}),
            ],
        ),
        (INFO1, [{"restrict_logfiles": [".*"]}], []),
        (
            INFO1,
            [
                {
                    "restrict_logfiles": [".*"],
                    "separate_checks": True,
                }
            ],
            [
                Service(item="log1", parameters={"expected_logfiles": ["log1"]}),
                Service(item="log2", parameters={"expected_logfiles": ["log2"]}),
                Service(item="log5", parameters={"expected_logfiles": ["log5"]}),
            ],
        ),
        (
            INFO1,
            [
                {
                    "restrict_logfiles": [".*"],
                    "separate_checks": False,
                }
            ],
            [],
        ),
        (
            INFO1,
            [
                {
                    "restrict_logfiles": [".*"],
                }
            ],
            [],
        ),
        (
            INFO1,
            [
                {
                    "restrict_logfiles": ["log1"],
                    "separate_checks": True,
                    "method": "pass me on!",
                    "facility": "pass me on!",
                    "monitor_logfilelist": "pass me on!",
                    "logwatch_reclassify": "pass me on!",
                    "some_other_key": "I should be discarded!",
                }
            ],
            [
                Service(
                    item="log1",
                    parameters={
                        "expected_logfiles": ["log1"],
                        "method": "pass me on!",
                        "facility": "pass me on!",
                        "monitor_logfilelist": "pass me on!",
                        "logwatch_reclassify": "pass me on!",
                    },
                ),
            ],
        ),
    ],
)
def test_logwatch_ec_inventory_single(monkeypatch, info, fwd_rule, expected_result):
    parsed = parse_logwatch(info)

    monkeypatch.setattr(logwatch_ec.logwatch, "get_ec_rule_params", lambda: fwd_rule)
    actual_result = sorted(logwatch_ec.discover_single(parsed), key=lambda s: s.item or "")
    assert actual_result == expected_result


@pytest.mark.parametrize(
    "info, fwd_rule, expected_result",
    [
        (INFO1, [], []),
        (INFO1, [{"separate_checks": True}], []),
        (
            INFO1,
            [{"separate_checks": False}],
            [
                Service(parameters={"expected_logfiles": ["log1", "log2", "log5"]}),
            ],
        ),
        (
            INFO1,
            [{"restrict_logfiles": [".*[12]"], "separate_checks": False}],
            [
                Service(parameters={"expected_logfiles": ["log1", "log2"]}),
            ],
        ),
    ],
)
def test_logwatch_ec_inventory_groups(monkeypatch, info, fwd_rule, expected_result):
    parsed = parse_logwatch(info)

    monkeypatch.setattr(logwatch_ec.logwatch, "get_ec_rule_params", lambda: fwd_rule)
    actual_result = list(logwatch_ec.discover_group(parsed))
    assert actual_result == expected_result


def test_check_logwatch_ec_common_single_node() -> None:
    assert list(
        logwatch_ec.check_logwatch_ec_common(
            "log1",
            {},
            {
                "node1": parse_logwatch(INFO1),
            },
            service_level=10,
        )
    ) == [
        Result(state=State.OK, summary="Forwarded 0 messages"),
        Metric("messages", 0.0),
    ]


def test_check_logwatch_ec_common_single_node_item_missing() -> None:
    assert not list(
        logwatch_ec.check_logwatch_ec_common(
            "log1",
            {},
            {
                "node1": parse_logwatch(INFO2),
            },
            service_level=10,
        )
    )


def test_check_logwatch_ec_common_multiple_nodes() -> None:
    assert list(
        logwatch_ec.check_logwatch_ec_common(
            "log1",
            {},
            {
                "node1": parse_logwatch(INFO1),
                "node2": parse_logwatch(INFO1),
            },
            service_level=10,
        )
    ) == [
        Result(state=State.OK, summary="Forwarded 0 messages"),
        Metric("messages", 0.0),
    ]


def test_check_logwatch_ec_common_multiple_nodes_item_completely_missing() -> None:
    assert not list(
        logwatch_ec.check_logwatch_ec_common(
            "log1",
            {},
            {
                "node1": parse_logwatch(INFO2),
                "node2": parse_logwatch(INFO2),
            },
            service_level=10,
        )
    )


def test_check_logwatch_ec_common_multiple_nodes_item_partially_missing() -> None:
    assert list(
        logwatch_ec.check_logwatch_ec_common(
            "log1",
            {},
            {
                "node1": parse_logwatch(INFO1),
                "node2": parse_logwatch(INFO2),
            },
            service_level=10,
        )
    ) == [
        Result(state=State.OK, summary="Forwarded 0 messages"),
        Metric("messages", 0.0),
    ]
