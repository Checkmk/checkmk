#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from cmk.base.check_api import MKCounterWrapped

pytestmark = pytest.mark.checks

result_parsed_over_time = [
    {
        "clustermode": {
            "clu1-01": {
                "cpu_busy": "0",
                "num_processors": "2",
                "nvram-battery-status": "battery_ok",
            },
        },
    },
    {
        "clustermode": {
            "clu1-01": {
                "cpu_busy": "8000000",
                "num_processors": "2",
                "nvram-battery-status": "battery_ok",
            }
        }
    },
    {
        "clustermode": {
            "clu1-01": {
                "cpu_busy": "9000000",
                "num_processors": "2",
                "nvram-battery-status": "battery_ok",
            }
        }
    },
]


@pytest.mark.parametrize(
    "params, first_result_change, second_result_change",
    [
        (
            {"levels": (80.0, 90.0)},
            (0, "Total CPU: 13.33%, 2 CPUs", [("util", 13.333333333333334, 80.0, 90.0, 0, 2)]),
            (0, "Total CPU: 0.83%, 2 CPUs", [("util", 0.8333333333333334, 80.0, 90.0, 0, 2)]),
        ),
        (
            {"levels": (10.0, 90.0)},
            (
                1,
                "Total CPU: 13.33% (warn/crit at 10.0%/90.0%), 2 CPUs",
                [("util", 13.333333333333334, 10.0, 90.0, 0, 2)],
            ),
            (0, "Total CPU: 0.83%, 2 CPUs", [("util", 0.8333333333333334, 10.0, 90.0, 0, 2)]),
        ),
        (
            {
                "levels": (80.0, 90.0),
                "average": 2,
            },
            (
                0,
                "Total CPU (2min average): 0%, 2 CPUs",
                [
                    ("util", 13.333333333333334, 80.0, 90.0, 0, 2),
                    ("util_average", 0, 80.0, 90.0, 0, 100),
                ],
            ),
            (
                0,
                "Total CPU (2min average): 0.42%, 2 CPUs",
                [
                    ("util", 0.8333333333333334, 80.0, 90.0, 0, 2),
                    ("util_average", 0.4166666666666667, 80.0, 90.0, 0, 100),
                ],
            ),
        ),
    ],
)
def test_cluster_mode_check_function(
    monkeypatch, params, first_result_change, second_result_change
):
    check = Check("netapp_api_cpu")
    monkeypatch.setattr("time.time", lambda: 0)
    try:
        check.run_check("clu1-01", params, result_parsed_over_time[0])
    except MKCounterWrapped:
        pass
    monkeypatch.setattr("time.time", lambda: 60)
    result = check.run_check("clu1-01", params, result_parsed_over_time[1])
    assert result == first_result_change
    monkeypatch.setattr("time.time", lambda: 180)
    result = check.run_check("clu1-01", params, result_parsed_over_time[2])
    assert result == second_result_change
