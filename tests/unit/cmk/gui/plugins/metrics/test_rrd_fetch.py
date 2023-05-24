#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from livestatus import SiteId

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.prediction import TimeSeries, TimeSeriesValues
from cmk.utils.type_defs import HostName

import cmk.gui.plugins.metrics.rrd_fetch as rf
from cmk.gui.config import active_config
from cmk.gui.plugins.metrics.utils import GraphDataRange, TemplateGraphRecipe
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


_GRAPH_RECIPE = TemplateGraphRecipe(
    {
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
                "host_name": HostName("my-host"),
                "service_description": "Temperature Zone 6",
                "graph_index": 0,
                "graph_id": "temperature",
            },
        ),
    }
)

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


@pytest.mark.parametrize(
    [
        "default_temperature_unit",
        "expected_data_points",
    ],
    [
        pytest.param(
            TemperatureUnit.CELSIUS,
            [
                53.69,
                52.0033,
                52.0933,
                52.6133,
                48.7208,
                None,
                None,
                None,
                None,
                None,
                49.15,
                50.2533,
                51.5817,
                44.275,
                40.3283,
                38.8817,
            ],
            id="without unit conversion",
        ),
        pytest.param(
            TemperatureUnit.FAHRENHEIT,
            [
                128.642,
                125.60594,
                125.76794,
                126.70394,
                119.69744,
                None,
                None,
                None,
                None,
                None,
                120.47,
                122.45594000000001,
                124.84706,
                111.695,
                104.59094,
                101.98706,
            ],
            id="with unit conversion",
        ),
    ],
)
def test_merge_multicol(
    default_temperature_unit: TemperatureUnit,
    expected_data_points: TimeSeriesValues,
) -> None:
    active_config.default_temperature_unit = default_temperature_unit.value
    assert rf.merge_multicol(
        {
            "rrddata:ambient_temp:ambient_temp.average:1682324616:1682497416:60": [0, 0, 0],
            "rrddata:ambient_temp:ambient_temp.average:1682490216:1682497416:60": [0, 0, 0],
            "rrddata:temp:temp.average:1682324616:1682497416:60": [
                1682324400,
                1682497800,
                600,
                53.69,
                52.0033,
                52.0933,
                52.6133,
                48.7208,
                None,
                None,
                None,
                None,
                None,
                49.15,
                50.2533,
                51.5817,
                44.275,
                40.3283,
                38.8817,
            ],
            "rrddata:temp:temp.average:1682490216:1682497416:60": [
                1682490180,
                1682497440,
                60,
                50.05,
                52.0167,
                53.9833,
                54.9833,
                55.05,
                55.05,
                55.05,
                54.2,
                54.05,
                54.05,
                54.05,
                54.05,
                54.05,
                54.05,
                54.05,
            ],
            "rrddata:temperature:temperature.average:1682324616:1682497416:60": [0, 0, 0],
            "rrddata:temperature:temperature.average:1682490216:1682497416:60": [0, 0, 0],
            "rrddata:value:value.average:1682324616:1682497416:60": [0, 0, 0],
            "rrddata:value:value.average:1682490216:1682497416:60": [0, 0, 0],
            "service_check_command": "check_mk-lnx_thermal",
        },
        [
            "rrddata:value:value.average:1682324616:1682497416:60",
            "rrddata:temp:temp.average:1682324616:1682497416:60",
            "rrddata:temperature:temperature.average:1682324616:1682497416:60",
            "rrddata:ambient_temp:ambient_temp.average:1682324616:1682497416:60",
        ],
        "temp",
    ) == TimeSeries(
        expected_data_points,
        timewindow=(1682324400, 1682497800, 600),
    )
