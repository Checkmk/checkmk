#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.gcp_gce import (
    CHECK_DEFAULT_PARAMETERS,
    check_disk_summary,
    check_network,
    parse_gce_uptime,
)
from cmk.base.plugins.agent_based.utils import gcp, uptime


def test_parse_piggy_back():
    uptime_section = parse_gce_uptime(
        [
            [
                '{"metric": {"type": "compute.googleapis.com/instance/uptime_total", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "tribe29-check-development", "instance_id": "4916403162284897775"}}, "metric_kind": 1, "value_type": 2, "points": [{"interval": {"start_time": "2022-05-05T13:55:15.478132Z", "end_time": "2022-05-05T13:55:15.478132Z"}, "value": {"int64_value": "10"}}], "unit": ""}'
            ],
        ]
    )
    assert uptime_section == uptime.Section(uptime_sec=10, message=None)


# test if I call the network check correct
NETWORK_SECTION = [
    [
        '{"metric": {"type": "compute.googleapis.com/instance/network/received_bytes_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "tribe29-check-development", "instance_id": "4916403162284897775"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-05-18T12:38:32.833429Z", "end_time": "2022-05-18T12:38:32.833429Z"}, "value": {"double_value": 385.4}}, {"interval": {"start_time": "2022-05-18T12:37:32.833429Z", "end_time": "2022-05-18T12:37:32.833429Z"}, "value": {"double_value": 894.0666666666667}}, {"interval": {"start_time": "2022-05-18T12:36:32.833429Z", "end_time": "2022-05-18T12:36:32.833429Z"}, "value": {"double_value": 717.3333333333334}}, {"interval": {"start_time": "2022-05-18T12:35:32.833429Z", "end_time": "2022-05-18T12:35:32.833429Z"}, "value": {"double_value": 280.25}}, {"interval": {"start_time": "2022-05-18T12:34:32.833429Z", "end_time": "2022-05-18T12:34:32.833429Z"}, "value": {"double_value": 144.31666666666666}}, {"interval": {"start_time": "2022-05-18T12:33:32.833429Z", "end_time": "2022-05-18T12:33:32.833429Z"}, "value": {"double_value": 40178.35}}, {"interval": {"start_time": "2022-05-18T12:32:32.833429Z", "end_time": "2022-05-18T12:32:32.833429Z"}, "value": {"double_value": 22187.466666666667}}, {"interval": {"start_time": "2022-05-18T12:31:32.833429Z", "end_time": "2022-05-18T12:31:32.833429Z"}, "value": {"double_value": 149.1}}, {"interval": {"start_time": "2022-05-18T12:30:32.833429Z", "end_time": "2022-05-18T12:30:32.833429Z"}, "value": {"double_value": 148.98333333333332}}, {"interval": {"start_time": "2022-05-18T12:29:32.833429Z", "end_time": "2022-05-18T12:29:32.833429Z"}, "value": {"double_value": 304.1}}, {"interval": {"start_time": "2022-05-18T12:28:32.833429Z", "end_time": "2022-05-18T12:28:32.833429Z"}, "value": {"double_value": 276.21666666666664}}, {"interval": {"start_time": "2022-05-18T12:27:32.833429Z", "end_time": "2022-05-18T12:27:32.833429Z"}, "value": {"double_value": 232.43333333333334}}, {"interval": {"start_time": "2022-05-18T12:26:32.833429Z", "end_time": "2022-05-18T12:26:32.833429Z"}, "value": {"double_value": 224.08333333333334}}, {"interval": {"start_time": "2022-05-18T12:25:32.833429Z", "end_time": "2022-05-18T12:25:32.833429Z"}, "value": {"double_value": 329.03333333333336}}, {"interval": {"start_time": "2022-05-18T12:24:32.833429Z", "end_time": "2022-05-18T12:24:32.833429Z"}, "value": {"double_value": 306.8833333333333}}, {"interval": {"start_time": "2022-05-18T12:23:32.833429Z", "end_time": "2022-05-18T12:23:32.833429Z"}, "value": {"double_value": 203.33333333333334}}, {"interval": {"start_time": "2022-05-18T12:22:32.833429Z", "end_time": "2022-05-18T12:22:32.833429Z"}, "value": {"double_value": 170.11666666666667}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "compute.googleapis.com/instance/network/sent_bytes_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "tribe29-check-development", "instance_id": "4916403162284897775"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-05-18T12:39:32.833429Z", "end_time": "2022-05-18T12:39:32.833429Z"}, "value": {"double_value": 245.26666666666668}}, {"interval": {"start_time": "2022-05-18T12:38:32.833429Z", "end_time": "2022-05-18T12:38:32.833429Z"}, "value": {"double_value": 225.58333333333334}}, {"interval": {"start_time": "2022-05-18T12:37:32.833429Z", "end_time": "2022-05-18T12:37:32.833429Z"}, "value": {"double_value": 111.25}}, {"interval": {"start_time": "2022-05-18T12:36:32.833429Z", "end_time": "2022-05-18T12:36:32.833429Z"}, "value": {"double_value": 59.63333333333333}}, {"interval": {"start_time": "2022-05-18T12:35:32.833429Z", "end_time": "2022-05-18T12:35:32.833429Z"}, "value": {"double_value": 58.333333333333336}}, {"interval": {"start_time": "2022-05-18T12:34:32.833429Z", "end_time": "2022-05-18T12:34:32.833429Z"}, "value": {"double_value": 58.7}}, {"interval": {"start_time": "2022-05-18T12:33:32.833429Z", "end_time": "2022-05-18T12:33:32.833429Z"}, "value": {"double_value": 232.53333333333333}}, {"interval": {"start_time": "2022-05-18T12:32:32.833429Z", "end_time": "2022-05-18T12:32:32.833429Z"}, "value": {"double_value": 137.93333333333334}}, {"interval": {"start_time": "2022-05-18T12:31:32.833429Z", "end_time": "2022-05-18T12:31:32.833429Z"}, "value": {"double_value": 61.25}}, {"interval": {"start_time": "2022-05-18T12:30:32.833429Z", "end_time": "2022-05-18T12:30:32.833429Z"}, "value": {"double_value": 59.85}}, {"interval": {"start_time": "2022-05-18T12:29:32.833429Z", "end_time": "2022-05-18T12:29:32.833429Z"}, "value": {"double_value": 56.53333333333333}}, {"interval": {"start_time": "2022-05-18T12:28:32.833429Z", "end_time": "2022-05-18T12:28:32.833429Z"}, "value": {"double_value": 36.43333333333333}}, {"interval": {"start_time": "2022-05-18T12:27:32.833429Z", "end_time": "2022-05-18T12:27:32.833429Z"}, "value": {"double_value": 30.366666666666667}}, {"interval": {"start_time": "2022-05-18T12:26:32.833429Z", "end_time": "2022-05-18T12:26:32.833429Z"}, "value": {"double_value": 67.53333333333333}}, {"interval":{"start_time": "2022-05-18T12:25:32.833429Z", "end_time": "2022-05-18T12:25:32.833429Z"}, "value": {"double_value": 107.86666666666666}}, {"interval": {"start_time": "2022-05-18T12:24:32.833429Z", "end_time": "2022-05-18T12:24:32.833429Z"}, "value": {"double_value": 123.6}}, {"interval": {"start_time": "2022-05-18T12:23:32.833429Z", "end_time": "2022-05-18T12:23:32.833429Z"}, "value": {"double_value": 111.33333333333333}}, {"interval": {"start_time": "2022-05-18T12:22:32.833429Z", "end_time": "2022-05-18T12:22:32.833429Z"}, "value": {"double_value": 60.45}}], "unit": ""}'
    ],
]


def test_network_check():
    section = gcp.parse_piggyback(NETWORK_SECTION)
    params = CHECK_DEFAULT_PARAMETERS
    item = "nic0"
    results = list(check_network(item, params, section))
    assert results == [
        Result(state=State.OK, summary="[0]"),
        Result(state=State.OK, summary="(up)", details="Operational state: up"),
        Result(state=State.OK, summary="Speed: unknown"),
        Metric("outqlen", 0.0),
        Result(state=State.OK, summary="In: 385 B/s"),
        Metric("in", 385.4, boundaries=(0.0, None)),
        Result(state=State.OK, summary="Out: 245 B/s"),
        Metric("out", 245.26666666666668, boundaries=(0.0, None)),
        Result(state=State.OK, notice="Errors in: 0%"),
        Metric("inerr", 0.0),
        Result(state=State.OK, notice="Multicast in: 0 packets/s"),
        Metric("inmcast", 0.0),
        Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
        Metric("inbcast", 0.0),
        Result(state=State.OK, notice="Unicast in: 0 packets/s"),
        Metric("inucast", 0.0),
        Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
        Metric("innucast", 0.0),
        Result(state=State.OK, notice="Discards in: 0 packets/s"),
        Metric("indisc", 0.0),
        Result(state=State.OK, notice="Errors out: 0%"),
        Metric("outerr", 0.0),
        Result(state=State.OK, notice="Multicast out: 0 packets/s"),
        Metric("outmcast", 0.0),
        Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
        Metric("outbcast", 0.0),
        Result(state=State.OK, notice="Unicast out: 0 packets/s"),
        Metric("outucast", 0.0),
        Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
        Result(state=State.OK, notice="Discards out: 0 packets/s"),
        Metric("outdisc", 0.0),
    ]


DISK_SECTION = [
    [
        '{"metric": {"type": "compute.googleapis.com/instance/disk/read_bytes_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"instance_id": "1807848413475835096", "project_id": "tribe29-check-development"}}, "metric_kind": 2, "value_type": 2, "points": [{"interval": {"start_time": "2022-05-23T12:57:11.921195Z", "end_time": "2022-05-23T12:58:11.921195Z"}, "value": {"int64_value": "2"}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "compute.googleapis.com/instance/disk/read_ops_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "tribe29-check-development", "instance_id": "1807848413475835096"}}, "metric_kind": 2, "value_type": 2, "points": [{"interval": {"start_time": "2022-05-23T12:57:11.921195Z", "end_time": "2022-05-23T12:58:11.921195Z"}, "value": {"int64_value": "4"}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "compute.googleapis.com/instance/disk/write_bytes_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"instance_id": "1807848413475835096", "project_id": "tribe29-check-development"}}, "metric_kind": 2, "value_type": 2, "points": [{"interval": {"start_time": "2022-05-23T12:57:11.921195Z", "end_time": "2022-05-23T12:58:11.921195Z"}, "value": {"int64_value": "8"}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "compute.googleapis.com/instance/disk/write_ops_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "tribe29-check-development", "instance_id": "1807848413475835096"}}, "metric_kind": 2, "value_type": 2, "points": [{"interval": {"start_time": "2022-05-23T12:57:11.921195Z", "end_time": "2022-05-23T12:58:11.921195Z"}, "value": {"int64_value": "16"}}], "unit": ""}'
    ],
]


def test_disk_summary_check():
    section = gcp.parse_piggyback(DISK_SECTION)
    params = {
        "disk_read_throughput": None,
        "disk_write_throughput": None,
        "disk_read_ios": None,
        "disk_write_ios": None,
    }
    results = list(check_disk_summary(params, section))
    assert results == [
        Result(state=State.OK, summary="Read: 2.00 B/s"),
        Metric("disk_read_throughput", 2.0),
        Result(state=State.OK, summary="Write: 8.00 B/s"),
        Metric("disk_write_throughput", 8.0),
        Result(state=State.OK, summary="Read operations: 4.0"),
        Metric("disk_read_ios", 4.0),
        Result(state=State.OK, summary="Write operations: 16.0"),
        Metric("disk_write_ios", 16.0),
    ]
