#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Iterable

import pytest

from cmk.utils.check_utils import ServiceCheckResult
from cmk.utils.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.utils.type_defs import LegacyCheckParameters

import cmk.base.agent_based.checking as checking
from cmk.base.api.agent_based.checking_classes import Metric, Result
from cmk.base.api.agent_based.checking_classes import State as state


def make_timespecific_params_list(
    entries: Iterable[LegacyCheckParameters],
) -> TimespecificParameters:
    return TimespecificParameters([TimespecificParameterSet.from_parameters(e) for e in entries])


@pytest.mark.parametrize(
    "rules,active_timeperiods,expected_result",
    [
        (make_timespecific_params_list([(1, 1), (2, 2)]), ["tp1", "tp2"], (1, 1)),
        (
            make_timespecific_params_list([(1, 1), {"tp_default_value": (2, 2), "tp_values": []}]),
            ["tp1", "tp2"],
            (1, 1),
        ),
        (
            make_timespecific_params_list([{"tp_default_value": (2, 2), "tp_values": []}, (1, 1)]),
            ["tp1", "tp2"],
            (2, 2),
        ),
        (
            make_timespecific_params_list(
                [{"tp_default_value": (2, 2), "tp_values": [("tp1", (3, 3))]}, (1, 1)]
            ),
            ["tp1", "tp2"],
            (3, 3),
        ),
        (
            make_timespecific_params_list(
                [
                    {"tp_default_value": (2, 2), "tp_values": [("tp2", (4, 4)), ("tp1", (3, 3))]},
                    (1, 1),
                ]
            ),
            ["tp1", "tp2"],
            (4, 4),
        ),
        (
            make_timespecific_params_list(
                [
                    {"tp_default_value": (2, 2), "tp_values": [("tp1", (4, 4)), ("tp3", (3, 3))]},
                    (1, 1),
                ]
            ),
            ["tp2"],
            (2, 2),
        ),
        (
            make_timespecific_params_list(
                [
                    (1, 1),
                    {"tp_default_value": (2, 2), "tp_values": [("tp1", (4, 4)), ("tp3", (3, 3))]},
                ]
            ),
            [],
            (1, 1),
        ),
        (make_timespecific_params_list([{1: 1}]), ["tp1", "tp2"], {1: 1}),
        (
            make_timespecific_params_list([{1: 1}, {"tp_default_value": {2: 2}, "tp_values": []}]),
            ["tp1", "tp2"],
            {1: 1, 2: 2},
        ),
        (
            make_timespecific_params_list(
                [{"tp_default_value": {2: 2}, "tp_values": [("tp1", {3: 3})]}, {1: 1}]
            ),
            ["tp1", "tp2"],
            {1: 1, 2: 2, 3: 3},
        ),
        (
            make_timespecific_params_list(
                [
                    {"tp_default_value": {2: 4}, "tp_values": [("tp1", {1: 5}), ("tp2", {3: 6})]},
                    {"tp_default_value": {2: 2}, "tp_values": [("tp1", {3: 3})]},
                    {1: 1},
                ]
            ),
            ["tp1", "tp2"],
            {1: 5, 2: 4, 3: 6},
        ),
        (
            make_timespecific_params_list(
                [
                    {"tp_default_value": {2: 4}, "tp_values": [("tp3", {1: 5}), ("tp2", {3: 6})]},
                    {"tp_default_value": {2: 2}, "tp_values": [("tp1", {3: 3})]},
                    {1: 1},
                ]
            ),
            ["tp1", "tp2"],
            {1: 1, 2: 4, 3: 6},
        ),
        (
            make_timespecific_params_list(
                [
                    {"tp_default_value": {2: 4}, "tp_values": [("tp3", {1: 5}), ("tp2", {3: 6})]},
                    {"tp_default_value": {2: 2}, "tp_values": [("tp1", {3: 3})]},
                    {1: 1},
                ]
            ),
            ["tp1"],
            {1: 1, 2: 4, 3: 3},
        ),
        # (Old) tuple based default params
        (
            make_timespecific_params_list(
                [
                    {
                        "tp_default_value": {"key": (1, 1)},
                        "tp_values": [
                            (
                                "tp",
                                {
                                    "key": (2, 2),
                                },
                            )
                        ],
                    },
                    (3, 3),
                ]
            ),
            ["tp"],
            {"key": (2, 2)},
        ),
        (
            make_timespecific_params_list(
                [
                    {
                        "tp_default_value": {"key": (1, 1)},
                        "tp_values": [
                            (
                                "tp",
                                {
                                    "key": (2, 2),
                                },
                            )
                        ],
                    },
                    (3, 3),
                ]
            ),
            [],
            {"key": (1, 1)},
        ),
        (
            make_timespecific_params_list(
                [
                    {
                        "tp_default_value": {},
                        "tp_values": [
                            (
                                "tp",
                                {
                                    "key": (2, 2),
                                },
                            )
                        ],
                    },
                    (3, 3),
                ]
            ),
            [],
            {},
        ),
    ],
)
def test_time_resolved_check_parameters(
    monkeypatch, rules: TimespecificParameters, active_timeperiods, expected_result
):
    assert expected_result == rules.evaluate(lambda tp: tp in active_timeperiods)


@pytest.mark.parametrize(
    "subresults, aggregated_results",
    [
        ([], ServiceCheckResult.item_not_found()),
        (
            [
                Result(state=state.OK, notice="details"),
            ],
            ServiceCheckResult(0, "Everything looks OK - 1 detail available\ndetails", []),
        ),
        (
            [
                Result(state=state.OK, summary="summary1", details="detailed info1"),
                Result(state=state.WARN, summary="summary2", details="detailed info2"),
            ],
            ServiceCheckResult(1, "summary1, summary2(!)\ndetailed info1\ndetailed info2(!)", []),
        ),
        (
            [
                Result(state=state.OK, summary="summary"),
                Metric(name="name", value=42),
            ],
            ServiceCheckResult(0, "summary\nsummary", [("name", 42.0, None, None, None, None)]),
        ),
    ],
)
def test_aggregate_result(subresults, aggregated_results: ServiceCheckResult) -> None:
    assert checking._aggregate_results(subresults) == aggregated_results
