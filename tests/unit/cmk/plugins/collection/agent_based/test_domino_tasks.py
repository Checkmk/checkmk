#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time

import pytest

from cmk.checkengine.parameters import Parameters

from cmk.agent_based.v1 import IgnoreResultsError, Metric, Result, State
from cmk.plugins.collection.agent_based.domino_tasks import check_domino_tasks
from cmk.plugins.lib import ps

SECTION_DOMINO_TASKS_DATA = (
    1,
    [
        (ps.PsInfo(), ["Admin Process"]),
        (ps.PsInfo(), ["Router"]),
        (ps.PsInfo(), ["Admin Process"]),
        (ps.PsInfo(), ["Admin Process"]),
        (ps.PsInfo(), ["Admin Process"]),
        (ps.PsInfo(), ["Cluster Replicator"]),
        (ps.PsInfo(), ["HTTP Server"]),
        (ps.PsInfo(), ["Cluster Directory"]),
        (ps.PsInfo(), ["Traveler"]),
        (ps.PsInfo(), ["Router"]),
        (ps.PsInfo(), ["Router"]),
        (ps.PsInfo(), ["Router"]),
        (ps.PsInfo(), ["Router"]),
        (ps.PsInfo(), ["Router"]),
        (ps.PsInfo(), ["Router"]),
        (ps.PsInfo(), ["Router"]),
        (ps.PsInfo(), ["Process Monitor"]),
        (ps.PsInfo(), ["Domino OSGi Tasklet Container"]),
        (ps.PsInfo(), ["Agent Manager"]),
        (ps.PsInfo(), ["Event Interceptor"]),
        (ps.PsInfo(), ["Rooms and Resources Manager"]),
        (ps.PsInfo(), ["QuerySet Handler"]),
        (ps.PsInfo(), ["Calendar Connector"]),
        (ps.PsInfo(), ["Directory Indexer"]),
        (ps.PsInfo(), ["Agent Manager"]),
        (ps.PsInfo(), ["Schedule Manager"]),
        (ps.PsInfo(), ["Admin Process"]),
        (ps.PsInfo(), ["Indexer"]),
        (ps.PsInfo(), ["Router"]),
        (ps.PsInfo(), ["Replicator"]),
        (ps.PsInfo(), ["Event Monitor"]),
    ],
    int(time.time()),
)


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "params, expected_result",
    [
        (
            Parameters({"process": None, "levels": (1, 1, 31, 41)}),
            [
                Result(state=State.OK, summary="Tasks: 31"),
                Metric("count", 31.0, levels=(32.0, 42.0), boundaries=(0.0, None)),
                Metric("pcpu", 0.0),
                Result(state=State.OK, summary="CPU: 0%"),
            ],
        ),
        (
            Parameters({"process": None, "levels": (35, 40, 50, 60)}),
            [
                Result(state=State.CRIT, summary="Tasks: 31 (warn/crit below 40/35)"),
                Metric("count", 31.0, levels=(51.0, 61.0), boundaries=(0.0, None)),
                Metric("pcpu", 0.0),
                Result(state=State.OK, summary="CPU: 0%"),
            ],
        ),
        (
            Parameters({"process": None, "levels": (1, 1, 32, 42)}),
            [
                Result(state=State.OK, summary="Tasks: 31"),
                Metric("count", 31.0, levels=(33.0, 43.0), boundaries=(0.0, None)),
                Metric("pcpu", 0.0),
                Result(state=State.OK, summary="CPU: 0%"),
            ],
        ),
    ],
)
def test_check_domino_tasks(params, expected_result):
    result = check_domino_tasks("mock_item", params, SECTION_DOMINO_TASKS_DATA, None)
    assert list(result) == expected_result


def test_check_domino_tasks_no_domino_data_goes_stale():
    with pytest.raises(IgnoreResultsError):
        list(check_domino_tasks("someitem", {}, None, {"somememstuff": 1}))
