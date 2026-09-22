#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.apc.agent_based.apc_inrow_airflow import (
    check_apc_inrow_airflow,
    inventory_apc_inrow_airflow,
    parse_apc_inrow_airflow,
)

PARAMS = {"level_low": (500.0, 200.0), "level_high": (1000.0, 1100.0)}


def test_discover_zero_airflow() -> None:
    assert list(inventory_apc_inrow_airflow(0.0)) == [Service()]


def test_air_irrc_airflow() -> None:
    assert parse_apc_inrow_airflow([[["600"]], []]) == 600.0


def test_cooling_unit_is_ignored_if_air_irrc_is_present() -> None:
    assert parse_apc_inrow_airflow([[["600"]], [["Airflow", "412", "L/s", "1"]]]) == 600.0


def test_cooling_unit_airflow_is_the_metric_unit_reading() -> None:
    assert (
        parse_apc_inrow_airflow(
            [
                [],
                [
                    ["Airflow", "874", "CFM", "1"],
                    ["Airflow", "412", "L/s", "1"],
                    ["Group Airflow", "876", "CFM", "1"],
                    ["Group Airflow", "413", "L/s", "1"],
                ],
            ]
        )
        == 412.0
    )


def test_no_airflow_means_no_section() -> None:
    assert parse_apc_inrow_airflow([[], [["Fan Speed", "30", "%", "1"]]]) is None


def test_check_warns_below_lower_level() -> None:
    assert list(check_apc_inrow_airflow(PARAMS, 412.0)) == [
        Result(state=State.WARN, summary="Current: 412 l/s too low"),
        Metric("airflow", 412.0, levels=(1000.0, 1100.0)),
    ]
