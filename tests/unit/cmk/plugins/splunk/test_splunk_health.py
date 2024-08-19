#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckResult, Result, State
from cmk.plugins.splunk.agent_based import splunk_health as health


def test_parse_splunk_health() -> None:
    string_table = [
        ["Overall_state", "green"],
        ["File_monitor_input", "red"],
        ["File_monitor_input", "Tailreader-0", "green"],
        ["File_monitor_input", "Batchreader-0", "red"],
    ]

    actual = health.parse_splunk_health(string_table)
    expected = [
        health.HealthItem(
            name=health.SplunkServiceName("Overall state"),
            health=health.HealthStatus.GREEN,
            features={},
        ),
        health.HealthItem(
            name=health.SplunkServiceName("File monitor input"),
            health=health.HealthStatus.RED,
            features={
                "Tailreader-0": health.HealthStatus.GREEN,
                "Batchreader-0": health.HealthStatus.RED,
            },
        ),
    ]

    assert actual == expected


def test_parse_splunk_health_does_not_parse_successfully_when_main_service_missing() -> None:
    string_table_missing_main_service_line = [["File_monitor_input", "Tailreader-0", "green"]]

    actual = health.parse_splunk_health(string_table_missing_main_service_line)
    expected: health.HealthSection = []

    assert actual == expected


def test_parse_splunk_health_does_not_parse_when_bad_value_passed_to_pydantic_model() -> None:
    bad_health_value = "cyan"
    string_table = [["File_monitor_input", bad_health_value]]

    actual = health.parse_splunk_health(string_table)
    expected: health.HealthSection = []

    assert actual == expected


def test_check_splunk_health() -> None:
    sections = [
        health.HealthItem(
            name=health.SplunkServiceName("Overall state"),
            health=health.HealthStatus.GREEN,
        ),
        health.HealthItem(
            name=health.SplunkServiceName("File monitor input"),
            health=health.HealthStatus.RED,
            features={
                "Tailreader-0": health.HealthStatus.GREEN,
                "Batchreader-0": health.HealthStatus.RED,
            },
        ),
    ]
    default_params: health.CheckParams = {
        "green": State.OK.value,
        "yellow": State.WARN.value,
        "red": State.CRIT.value,
    }

    actual = list(health.check_splunk_health(params=default_params, section=sections))
    expected: CheckResult = [
        Result(
            state=State.OK,
            summary="Overall state: green",
        ),
        Result(
            state=State.CRIT,
            summary="File monitor input: red (Batchreader-0: red, Tailreader-0: green)",
        ),
    ]

    assert actual == expected


def test_check_splunk_health_custom_params_sets_red_to_warn() -> None:
    sections = [
        health.HealthItem(
            name=health.SplunkServiceName("Overall state"),
            health=health.HealthStatus.RED,
        )
    ]
    custom_params: health.CheckParams = {
        "green": State.OK.value,
        "yellow": State.WARN.value,
        "red": State.WARN.value,
    }

    actual = list(health.check_splunk_health(params=custom_params, section=sections))
    expected: CheckResult = [Result(state=State.WARN, summary="Overall state: red")]

    assert actual == expected
