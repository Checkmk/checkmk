#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

# No stub file
import pytest  # type: ignore[import]
import cmk.base.core
import cmk.base.config
import cmk.base.checking
from cmk.base.api.agent_based.checking_classes import Result, State as state, Metric


@pytest.mark.parametrize(
    "rules,active_timeperiods,expected_result",
    [
        # Tuple based
        ((1, 1), ["tp1", "tp2"], (1, 1)),
        (cmk.base.config.TimespecificParamList([(1, 1), (2, 2)]), ["tp1", "tp2"], (1, 1)),
        (cmk.base.config.TimespecificParamList([(1, 1), {
            "tp_default_value": (2, 2),
            "tp_values": []
        }]), ["tp1", "tp2"], (1, 1)),
        (cmk.base.config.TimespecificParamList([{
            "tp_default_value": (2, 2),
            "tp_values": []
        }, (1, 1)]), ["tp1", "tp2"], (2, 2)),
        (cmk.base.config.TimespecificParamList([{
            "tp_default_value": (2, 2),
            "tp_values": [("tp1", (3, 3))]
        }, (1, 1)]), ["tp1", "tp2"], (3, 3)),
        (cmk.base.config.TimespecificParamList([{
            "tp_default_value": (2, 2),
            "tp_values": [("tp2", (4, 4)), ("tp1", (3, 3))]
        }, (1, 1)]), ["tp1", "tp2"], (4, 4)),
        (cmk.base.config.TimespecificParamList([{
            "tp_default_value": (2, 2),
            "tp_values": [("tp1", (4, 4)), ("tp3", (3, 3))]
        }, (1, 1)]), ["tp2"], (2, 2)),
        (cmk.base.config.TimespecificParamList([(1, 1), {
            "tp_default_value": (2, 2),
            "tp_values": [("tp1", (4, 4)), ("tp3", (3, 3))]
        }]), [], (1, 1)),
        # Dict based
        ({
            1: 1
        }, ["tp1", "tp2"], {
            1: 1
        }),
        (cmk.base.config.TimespecificParamList([{
            1: 1
        }]), ["tp1", "tp2"], {
            1: 1
        }),
        (cmk.base.config.TimespecificParamList([{
            1: 1
        }, {
            "tp_default_value": {
                2: 2
            },
            "tp_values": []
        }]), ["tp1", "tp2"], {
            1: 1,
            2: 2
        }),
        (cmk.base.config.TimespecificParamList([{
            "tp_default_value": {
                2: 2
            },
            "tp_values": [("tp1", {
                3: 3
            })]
        }, {
            1: 1
        }]), ["tp1", "tp2"], {
            1: 1,
            2: 2,
            3: 3
        }),
        (cmk.base.config.TimespecificParamList([{
            "tp_default_value": {
                2: 4
            },
            "tp_values": [("tp1", {
                1: 5
            }), ("tp2", {
                3: 6
            })]
        }, {
            "tp_default_value": {
                2: 2
            },
            "tp_values": [("tp1", {
                3: 3
            })]
        }, {
            1: 1
        }]), ["tp1", "tp2"], {
            1: 5,
            2: 4,
            3: 6
        }),
        (cmk.base.config.TimespecificParamList([{
            "tp_default_value": {
                2: 4
            },
            "tp_values": [("tp3", {
                1: 5
            }), ("tp2", {
                3: 6
            })]
        }, {
            "tp_default_value": {
                2: 2
            },
            "tp_values": [("tp1", {
                3: 3
            })]
        }, {
            1: 1
        }]), ["tp1", "tp2"], {
            1: 1,
            2: 4,
            3: 6
        }),
        (cmk.base.config.TimespecificParamList([{
            "tp_default_value": {
                2: 4
            },
            "tp_values": [("tp3", {
                1: 5
            }), ("tp2", {
                3: 6
            })]
        }, {
            "tp_default_value": {
                2: 2
            },
            "tp_values": [("tp1", {
                3: 3
            })]
        }, {
            1: 1
        }]), ["tp1"], {
            1: 1,
            2: 4,
            3: 3
        }),
        # (Old) tuple based default params
        (cmk.base.config.TimespecificParamList([
            {
                "tp_default_value": {
                    "key": (1, 1)
                },
                "tp_values": [("tp", {
                    "key": (2, 2),
                })]
            },
            (3, 3),
        ]), ["tp"], {
            "key": (2, 2)
        }),
        (cmk.base.config.TimespecificParamList([
            {
                "tp_default_value": {
                    "key": (1, 1)
                },
                "tp_values": [("tp", {
                    "key": (2, 2),
                })]
            },
            (3, 3),
        ]), [], {
            "key": (1, 1)
        }),
        (cmk.base.config.TimespecificParamList([
            {
                "tp_default_value": {},
                "tp_values": [("tp", {
                    "key": (2, 2),
                })]
            },
            (3, 3),
        ]), [], {}),
    ])
def test_determine_check_parameters(monkeypatch, rules, active_timeperiods, expected_result):
    monkeypatch.setattr(cmk.base.core, "timeperiod_active",
                        lambda tp: _check_timeperiod(tp, active_timeperiods))

    determined_check_params = cmk.base.checking.legacy_determine_check_params(rules)
    assert expected_result == determined_check_params, (
        "Determine params: Expected '%s' but got '%s'" % (expected_result, determined_check_params))


def _check_timeperiod(timeperiod, active_timeperiods):
    return timeperiod in active_timeperiods


@pytest.mark.parametrize("subresults, aggregated_results", [
    ([], cmk.base.checking.ITEM_NOT_FOUND),
    ([
        Result(state=state.OK, notice="details"),
    ], (0, "Everything looks OK - 1 detail available\ndetails", [])),
    ([
        Result(state=state.OK, summary="summary1", details="detailed info1"),
        Result(state=state.WARN, summary="summary2", details="detailed info2"),
    ], (1, "summary1, summary2(!)\ndetailed info1\ndetailed info2(!)", [])),
    ([
        Result(state=state.OK, summary="summary"),
        Metric(name="name", value=42),
    ], (0, "summary\nsummary", [("name", 42.0, None, None, None, None)])),
])
def test_aggregate_result(subresults, aggregated_results):
    assert cmk.base.checking._aggregate_results(subresults) == aggregated_results
