#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

import cmk.plugins.netapp.agent_based.netapp_ontap_vs_traffic as ontap_vs_traffic
from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.netapp.agent_based.netapp_ontap_vs_traffic import (
    check_netapp_ontap_vs_traffic,
    discovery_netapp_ontap_vs_traffic,
    parse_netapp_ontap_vs_traffic,
)
from cmk.plugins.netapp.models import SvmTrafficCountersModel

NOW_SIMULATED = "1988-06-08 17:00:00.000000"
NOW_SIMULATED_SECONDS = (
    datetime.strptime(NOW_SIMULATED, "%Y-%m-%d %H:%M:%S.%f") - datetime(1970, 1, 1)
).total_seconds()
LAST_TIME_EPOCH = (
    datetime.strptime("1988-06-08 16:00:00.000000", "%Y-%m-%d %H:%M:%S.%f") - datetime(1970, 1, 1)
).total_seconds()


def _iscsi_lif_section(counters: Mapping[str, int]) -> ontap_vs_traffic.Section:
    return {
        "iscsi_lif.svm1": SvmTrafficCountersModel(
            svm_name="svm1",
            table="iscsi_lif",
            counters=[{"name": name, "value": value} for name, value in counters.items()],
        )
    }


def test_parse_netapp_ontap_vs_traffic() -> None:
    section = parse_netapp_ontap_vs_traffic(
        [['{"svm_name": "svm1", "table": "iscsi_lif", "counters": []}']]
    )

    assert list(section) == ["iscsi_lif.svm1"]


def test_discovery_netapp_ontap_vs_traffic() -> None:
    section = _iscsi_lif_section({})

    assert list(discovery_netapp_ontap_vs_traffic(section)) == [Service(item="svm1")]


def test_check_netapp_ontap_vs_traffic_iscsi_latency(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    The iSCSI latency counters are cumulative averages in microseconds.

    They have to be divided by the corresponding operations counter and rendered as
    milliseconds. The counter values are the ones observed on a customer system:
    33473556901556 / 19186784006 == 1744.62 us == 1.74 ms.
    """
    value_store = {
        # the latency counters are rated against their operations counter, so the "time"
        # slot holds the last operations count instead of a timestamp
        #                                     last ops, last scaled value
        "iscsi_lif.average_read_latency": (0, 0.0),
        "iscsi_lif.average_write_latency": (0, 0.0),
        #                        last time, last value
        "iscsi_lif.read_data": (LAST_TIME_EPOCH, 0),
        "iscsi_lif.write_data": (LAST_TIME_EPOCH, 0),
    }
    monkeypatch.setattr(ontap_vs_traffic, "get_value_store", lambda: value_store)

    section = _iscsi_lif_section(
        {
            "average_read_latency": 33473556901556,
            "average_write_latency": 4000000,
            "iscsi_read_ops": 19186784006,
            "iscsi_write_ops": 2000,
            "read_data": 0,
            "write_data": 0,
        }
    )

    with time_machine.travel(datetime.fromtimestamp(NOW_SIMULATED_SECONDS, tz=ZoneInfo("UTC"))):
        result = list(check_netapp_ontap_vs_traffic("svm1", {}, section))

    assert result == [
        Result(state=State.OK, summary="iSCSI avg. Read latency: 1.74 ms"),
        Metric("iscsi_read_latency", 0.001744615298274495),
        Result(state=State.OK, summary="iSCSI avg. Write latency: 2.00 ms"),
        Metric("iscsi_write_latency", 0.002),
        Result(state=State.OK, summary="iSCSI read data: 0 B"),
        Metric("iscsi_read_data", 0.0),
        Result(state=State.OK, summary="iSCSI write data: 0 B"),
        Metric("iscsi_write_data", 0.0),
    ]


def test_check_netapp_ontap_vs_traffic_latency_levels(monkeypatch: pytest.MonkeyPatch) -> None:
    """The levels of the ruleset are in seconds, the unit of the latency metrics."""
    value_store = {
        "iscsi_lif.average_read_latency": (0, 0.0),
        "iscsi_lif.read_data": (LAST_TIME_EPOCH, 0),
    }
    monkeypatch.setattr(ontap_vs_traffic, "get_value_store", lambda: value_store)

    section = _iscsi_lif_section(
        {
            # 33473556901556 / 19186784006 == 1744.62 us == 0.00174 s
            "average_read_latency": 33473556901556,
            "iscsi_read_ops": 19186784006,
            "read_data": 0,
        }
    )
    params = {"read_latency_levels": ("fixed", (0.001, 0.005))}

    with time_machine.travel(datetime.fromtimestamp(NOW_SIMULATED_SECONDS, tz=ZoneInfo("UTC"))):
        result = list(check_netapp_ontap_vs_traffic("svm1", params, section))

    assert result == [
        Result(
            state=State.WARN,
            summary="iSCSI avg. Read latency: 1.74 ms (warn/crit at 1.00 ms/5.00 ms)",
        ),
        Metric("iscsi_read_latency", 0.001744615298274495, levels=(0.001, 0.005)),
        Result(state=State.OK, summary="iSCSI read data: 0 B"),
        Metric("iscsi_read_data", 0.0),
    ]


def test_check_netapp_ontap_vs_traffic_iscsi_latency_without_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without operations in the interval there is no latency to average over."""
    value_store = {
        "iscsi_lif.average_read_latency": (19186784006, 33.473556901556),
        "iscsi_lif.read_data": (LAST_TIME_EPOCH, 0),
    }
    monkeypatch.setattr(ontap_vs_traffic, "get_value_store", lambda: value_store)

    section = _iscsi_lif_section(
        {
            "average_read_latency": 33473556901556,
            "iscsi_read_ops": 19186784006,
            "read_data": 0,
        }
    )

    with time_machine.travel(datetime.fromtimestamp(NOW_SIMULATED_SECONDS, tz=ZoneInfo("UTC"))):
        result = list(check_netapp_ontap_vs_traffic("svm1", {}, section))

    assert result == [
        Result(state=State.OK, summary="iSCSI avg. Read latency: -"),
        Result(state=State.OK, summary="iSCSI read data: 0 B"),
        Metric("iscsi_read_data", 0.0),
    ]
