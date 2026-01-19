#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.resulttype import OK, Result
from cmk.ccc.site import SiteId
from cmk.gui.graphing._fetch_time_series import fetch_augmented_time_series
from cmk.gui.graphing._from_api import RegisteredMetric
from cmk.gui.graphing._graph_metric_expressions import (
    AugmentedTimeSeries,
    GraphMetricRRDSource,
    QueryData,
    QueryDataError,
    TimeSeriesMetaData,
)
from cmk.gui.graphing._graph_specification import (
    GraphDataRange,
    GraphMetric,
    GraphRecipe,
)
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification
from cmk.gui.graphing._legacy import CheckMetricEntry
from cmk.gui.graphing._rrd import (
    _reverse_translate_into_all_potentially_relevant_metrics,
    translate_and_merge_rrd_columns,
)
from cmk.gui.graphing._time_series import TimeSeries, TimeSeriesValues
from cmk.gui.graphing._translated_metrics import TranslationSpec
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.unit_formatter import AutoPrecision
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.utils.metrics import MetricName


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


_GRAPH_RECIPE = GraphRecipe(
    title="Temperature",
    metrics=[
        GraphMetric(
            title="Temperature",
            line_type="area",
            operation=GraphMetricRRDSource(
                site_id=SiteId("NO_SITE"),
                host_name=HostName("my-host"),
                service_name="Temperature Zone 6",
                metric_name="temp",
                consolidation_func_name="max",
                scale=1,
            ),
            color="#ffa000",
            unit=ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="°C"), precision=AutoPrecision(digits=2)
            ),
        )
    ],
    unit_spec=ConvertibleUnitSpecification(
        notation=DecimalNotation(symbol="°C"),
        precision=AutoPrecision(digits=2),
    ),
    explicit_vertical_range=None,
    horizontal_rules=[],
    omit_zero_metrics=False,
    consolidation_function="max",
    specification=TemplateGraphSpecification(
        site=SiteId("NO_SITE"),
        host_name=HostName("my-host"),
        service_description="Temperature Zone 6",
        graph_index=0,
        graph_id="temperature",
    ),
)

_GRAPH_DATA_RANGE = GraphDataRange(time_range=(1681985455, 1681999855), step=20)


def _fetch() -> Iterator[Result[QueryData, QueryDataError]]:
    yield OK({})


def test_fetch_augmented_time_series(
    mock_livestatus: MockLiveStatusConnection, request_context: None
) -> None:
    with _setup_livestatus(mock_livestatus):
        assert [
            r.ok
            for r in fetch_augmented_time_series(
                {},
                _GRAPH_RECIPE,
                _GRAPH_DATA_RANGE,
                temperature_unit=TemperatureUnit.CELSIUS,
                backend_time_series_fetcher=lambda *args, **kwargs: _fetch(),
            )
            if r.is_ok()
        ] == [
            AugmentedTimeSeries(
                time_series=TimeSeries(start=1, end=2, step=3, values=[4, 5, None]),
                meta_data=TimeSeriesMetaData(
                    title="Temperature",
                    line_type="area",
                    color="#ffa000",
                    attributes={},
                ),
            ),
        ]


def test_fetch_augmented_time_series_with_conversion(
    mock_livestatus: MockLiveStatusConnection, request_context: None
) -> None:
    with _setup_livestatus(mock_livestatus):
        assert [
            r.ok
            for r in fetch_augmented_time_series(
                {},
                _GRAPH_RECIPE,
                _GRAPH_DATA_RANGE,
                temperature_unit=TemperatureUnit.FAHRENHEIT,
                backend_time_series_fetcher=lambda *args, **kwargs: _fetch(),
            )
            if r.is_ok()
        ] == [
            AugmentedTimeSeries(
                time_series=TimeSeries(start=1, end=2, step=3, values=[39.2, 41.0, None]),
                meta_data=TimeSeriesMetaData(
                    title="Temperature",
                    line_type="area",
                    color="#ffa000",
                    attributes={},
                ),
            ),
        ]


def test_translate_and_merge_rrd_columns() -> None:
    assert translate_and_merge_rrd_columns(
        MetricName("my_metric"),
        [
            (
                "rrddata:my_metric:my_metric.average:1682324616:1682497416:60",
                [1682324400, 1682497800, 600, 1, 2, 3, 4],
            )
        ],
        {},
        {},
        temperature_unit=TemperatureUnit.CELSIUS,
    ) == TimeSeries(
        start=1682324400,
        end=1682497800,
        step=600,
        values=[1, 2, 3, 4],
    )


def test_translate_and_merge_rrd_columns_with_translation() -> None:
    assert translate_and_merge_rrd_columns(
        MetricName("my_metric"),
        [
            (
                "rrddata:my_metric:my_metric.average:1682324616:1682497416:60",
                [1682324400, 1682497800, 600, None, None, 3, 4],
            ),
            (
                "rrddata:my_old_metric:my_old_metric.average:1682324616:1682497416:60",
                [1682324400, 1682497800, 600, 1, 2, None, None],
            ),
        ],
        {
            "my_old_metric": TranslationSpec(
                name="my_metric",
                scale=10,
                auto_graph=True,
                deprecated="",
            )
        },
        {},
        temperature_unit=TemperatureUnit.CELSIUS,
    ) == TimeSeries(
        start=1682324400,
        end=1682497800,
        step=600,
        values=[10, 20, 3, 4],
    )


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
                55.05,
                55.05,
                54.2,
                54.05,
                54.05,
                49.15,
                50.2533,
                51.5817,
                44.275,
                40.3283,
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
                131.09,
                131.09,
                129.56,
                129.29,
                129.29,
                120.47,
                122.45594000000001,
                124.84706,
                111.695,
                104.59094,
            ],
            id="with unit conversion",
        ),
    ],
)
def test_translate_and_merge_rrd_columns_unit_conversion(
    default_temperature_unit: TemperatureUnit,
    expected_data_points: TimeSeriesValues,
) -> None:
    assert translate_and_merge_rrd_columns(
        MetricName("temp"),
        [
            ("rrddata:ambient_temp:ambient_temp.average:1682324616:1682497416:60", [0, 0, 0]),
            (
                "rrddata:temp:temp.average:1682324616:1682497416:60",
                [
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
            ),
            (
                "rrddata:temp:temp.average:1682490216:1682497416:60",
                [
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
            ),
            ("rrddata:temperature:temperature.average:1682324616:1682497416:60", [0, 0, 0]),
        ],
        {},
        {
            "temp": RegisteredMetric(
                name="temp",
                title_localizer=lambda _localizer: "Temperature",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol="°C"),
                    precision=AutoPrecision(digits=2),
                ),
                color="",
            )
        },
        temperature_unit=default_temperature_unit,
    ) == TimeSeries(
        start=1682324400,
        end=1682497800,
        step=600,
        values=expected_data_points,
    )


@pytest.mark.parametrize(
    ["canonical_name", "current_version", "translations", "expected_result"],
    [
        pytest.param(
            MetricName("my_metric"),
            123,
            [
                {
                    MetricName("some_metric_1"): {"scale": 10},
                    MetricName("some_metric_2"): {
                        "scale": 10,
                        "name": MetricName("new_metric_name"),
                    },
                }
            ],
            {MetricName("my_metric")},
            id="no applicable translations",
        ),
        pytest.param(
            MetricName("my_metric"),
            2030020100,
            [
                {
                    MetricName("some_metric_1"): {"scale": 10},
                    MetricName("old_name_1"): {
                        "scale": 10,
                        "name": MetricName("my_metric"),
                    },
                },
                {
                    MetricName("old_name_1"): {
                        "name": MetricName("my_metric"),
                    },
                },
                {
                    MetricName("old_name_2"): {
                        "name": MetricName("my_metric"),
                    },
                    MetricName("irrelevant"): {"name": MetricName("still_irrelevant")},
                },
                {
                    MetricName("old_name_deprecated"): {
                        "name": MetricName("my_metric"),
                        "deprecated": "2.0.0i1",
                    },
                },
            ],
            {
                MetricName("my_metric"),
                MetricName("old_name_1"),
                MetricName("old_name_2"),
            },
            id="some applicable and one deprecated translation",
        ),
        pytest.param(
            MetricName("my_metric"),
            2030020100,
            [
                {
                    MetricName("old_name_1"): {
                        "name": MetricName("my_metric"),
                    },
                },
                {
                    "~.*expr": {
                        "name": MetricName("my_metric"),
                    },
                },
            ],
            {
                MetricName("my_metric"),
                MetricName("old_name_1"),
            },
            id="regex translation",
        ),
    ],
)
def test_reverse_translate_into_all_potentially_relevant_metrics(
    canonical_name: MetricName,
    current_version: int,
    translations: Iterable[Mapping[MetricName, CheckMetricEntry]],
    expected_result: frozenset[MetricName],
) -> None:
    assert (
        _reverse_translate_into_all_potentially_relevant_metrics(
            canonical_name,
            current_version,
            translations,
        )
        == expected_result
    )
