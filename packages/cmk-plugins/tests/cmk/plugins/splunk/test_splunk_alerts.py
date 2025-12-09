#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.splunk.agent_based import splunk_alerts as plugin


def test_parse_splunk_alerts() -> None:
    string_table = [["5"]]

    actual = plugin.parse_splunk_alerts(string_table)
    expected = plugin.AlertCount(5)

    assert actual == expected


def test_parse_splunk_alerts_ignores_bad_agent_output() -> None:
    string_table = [["foo"]]

    actual = plugin.parse_splunk_alerts(string_table)
    expected = None

    assert actual == expected


def test_check_splunk_alerts() -> None:
    sections = plugin.AlertCount(5)
    default_params = plugin.CheckParams(alerts=("fixed", (0, 0)))

    actual = list(plugin.check_splunk_alerts(params=default_params, section=sections))
    expected: CheckResult = [
        Result(state=State.CRIT, summary="Number of fired alerts: 5 (warn/crit at 0/0)"),
        Metric("fired_alerts", 5.0, levels=(0.0, 0.0)),
    ]

    assert actual == expected


def test_check_splunk_alerts_custom_params() -> None:
    sections = plugin.AlertCount(5)
    custom_params = plugin.CheckParams(alerts=("fixed", (3, 6)))

    actual = list(plugin.check_splunk_alerts(params=custom_params, section=sections))
    expected: CheckResult = [
        Result(state=State.WARN, summary="Number of fired alerts: 5 (warn/crit at 3/6)"),
        Metric("fired_alerts", 5.0, levels=(3.0, 6.0)),
    ]

    assert actual == expected
