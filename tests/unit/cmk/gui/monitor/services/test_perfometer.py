#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import perfometers
from cmk.graphing_engine import ApiPerfometer, PerfometerIndex
from cmk.gui.monitor.services._api._perfometer import ServicePerfometer

pytestmark = pytest.mark.usefixtures("request_context")

_HOSTNAME = "web-1"
_SERVICE_NAME = "CPU load"
_CHECK_COMMAND = "check_mk-test"


def _registered(perfometer: ApiPerfometer) -> PerfometerIndex:
    return PerfometerIndex({perfometer.name: perfometer})


def _bar(metric_name: str) -> perfometers.Perfometer:
    return perfometers.Perfometer(
        name=metric_name,
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
        segments=[metric_name],
    )


_SINGLE = _registered(_bar("single_metric"))
_STACKED = _registered(
    perfometers.Stacked(
        name="test_stacked",
        upper=_bar("upper_metric"),
        lower=_bar("lower_metric"),
    )
)
_BIDIRECTIONAL = _registered(
    perfometers.Bidirectional(
        name="test_bidirectional",
        left=_bar("left_metric"),
        right=_bar("right_metric"),
    )
)


def _perfometer(perf_data: str, registered_perfometers: PerfometerIndex) -> ServicePerfometer:
    perfometer = ServicePerfometer.from_perf_data(
        perf_data,
        _CHECK_COMMAND,
        host_name=_HOSTNAME,
        service_name=_SERVICE_NAME,
        registered_perfometers=registered_perfometers,
    )
    assert perfometer is not None
    return perfometer


def _shares(perfometer: ServicePerfometer) -> list[list[float]]:
    return [[segment.share for segment in bar] for bar in perfometer.bars]


def _colored(perfometer: ServicePerfometer) -> list[list[bool]]:
    return [[segment.color is not None for segment in bar] for bar in perfometer.bars]


def test_a_single_perfometer_is_one_bar_filled_up_to_its_value() -> None:
    perfometer = _perfometer("single_metric=42;;;0;100", _SINGLE)

    assert _shares(perfometer) == [[42.0, 58.0]]
    assert _colored(perfometer) == [[True, False]]
    assert perfometer.formatted == "42"


def test_a_stacked_perfometer_keeps_both_bars_upper_first() -> None:
    perfometer = _perfometer("upper_metric=70;;;0;100 lower_metric=30;;;0;100", _STACKED)

    assert _shares(perfometer) == [[70.0, 30.0], [30.0, 70.0]]
    assert _colored(perfometer) == [[True, False], [True, False]]


def test_the_label_of_a_stacked_perfometer_names_as_many_values_as_there_are_bars() -> None:
    perfometer = _perfometer("upper_metric=70;;;0;100 lower_metric=30;;;0;100", _STACKED)

    assert perfometer.formatted == "70 / 30"
    assert len(perfometer.bars) == 2


def test_a_bidirectional_perfometer_is_one_bar_growing_outwards_from_its_centre() -> None:
    perfometer = _perfometer("left_metric=50;;;0;100 right_metric=25;;;0;100", _BIDIRECTIONAL)

    assert _shares(perfometer) == [[25.0, 25.0, 12.5, 37.5]]
    assert _colored(perfometer) == [[False, True, True, False]]
    assert perfometer.formatted == "50 / 25"


def test_performance_data_matching_no_perfometer_has_none() -> None:
    assert (
        ServicePerfometer.from_perf_data(
            "unknown_metric=42;;;0;100",
            _CHECK_COMMAND,
            host_name=_HOSTNAME,
            service_name=_SERVICE_NAME,
            registered_perfometers=_SINGLE,
        )
        is None
    )
