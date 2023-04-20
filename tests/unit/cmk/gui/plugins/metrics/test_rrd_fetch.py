#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager

from livestatus import SiteId

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.prediction import TimeSeries

import cmk.gui.plugins.metrics.rrd_fetch as rf
from cmk.gui.config import active_config
from cmk.gui.plugins.metrics.utils import GraphDataRange
from cmk.gui.utils.temperate_unit import TemperatureUnit


def test_needed_elements_of_expression() -> None:
    assert set(
        rf.needed_elements_of_expression(
            (
                "transformation",
                ("q90percentile", 95.0),
                [("rrd", "heute", "CPU utilization", "util", "max")],
            ),
            lambda *args: (),
        )
    ) == {("heute", "CPU utilization", "util", "max")}


@contextmanager
def _setup_livestatus(mock_livestatus: MockLiveStatusConnection) -> Iterator[None]:
    with mock_livestatus(expect_status_query=True) as mock_live:
        mock_live.add_table(
            "services",
            [
                {
                    "host_name": "my-host",
                    "service_description": "Temperature Zone 6",
                    "rrddata:temp:temp.max:1681985455:1681999855:20": [1, 2, 3, 4, 5, None],
                }
            ],
        )
        mock_live.expect_query(
            """GET services
Columns: rrddata:temp:temp.max:1681985455:1681999855:20
Filter: host_name = my-host
Filter: service_description = Temperature Zone 6
ColumnHeaders: off

            """,
            sites=["NO_SITE"],
        )
        yield


_GRAPH_RECIPE = {
    "title": "Temperature",
    "metrics": [
        {
            "title": "Temperature",
            "line_type": "area",
            "expression": (
                "rrd",
                "NO_SITE",
                "my-host",
                "Temperature Zone 6",
                "temp",
                "max",
                1,
            ),
            "color": "#ffa000",
            "unit": "c",
        }
    ],
    "unit": "c",
    "explicit_vertical_range": (None, None),
    "horizontal_rules": [],
    "omit_zero_metrics": False,
    "consolidation_function": "max",
    "specification": (
        "template",
        {
            "site": SiteId("NO_SITE"),
            "host_name": "my-host",
            "service_description": "Temperature Zone 6",
            "graph_index": 0,
            "graph_id": "temperature",
        },
    ),
}


_GRAPH_DATA_RANGE: GraphDataRange = {"time_range": (1681985455, 1681999855), "step": 20}


def test_fetch_rrd_data_for_graph(mock_livestatus: MockLiveStatusConnection) -> None:
    with _setup_livestatus(mock_livestatus):
        assert rf.fetch_rrd_data_for_graph(
            _GRAPH_RECIPE,
            _GRAPH_DATA_RANGE,
            lambda _specs: (),
        ) == {
            ("NO_SITE", "my-host", "Temperature Zone 6", "temp", "max", 1): TimeSeries(
                [4, 5, None],
                timewindow=(1, 2, 3),
            )
        }


def test_fetch_rrd_data_for_graph_with_conversion(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    active_config.default_temperature_unit = TemperatureUnit.FAHRENHEIT.value
    with _setup_livestatus(mock_livestatus):
        assert rf.fetch_rrd_data_for_graph(
            _GRAPH_RECIPE,
            _GRAPH_DATA_RANGE,
            lambda _specs: (),
        ) == {
            ("NO_SITE", "my-host", "Temperature Zone 6", "temp", "max", 1): TimeSeries(
                [39.2, 41.0, None],
                timewindow=(1, 2, 3),
            )
        }
