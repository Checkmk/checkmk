#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

import json

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, ServiceLabel, State
from cmk.plugins.jenkins.agent_based.jenkins_nodes import (
    CHECK_DEFAULT_PARAMETERS,
    check_jenkins_nodes,
    discover_jenkins_nodes,
    parse_jenkins_nodes,
    Section,
)


@pytest.fixture(scope="module", name="section")
def _section() -> Section:
    return parse_jenkins_nodes(
        [
            [
                json.dumps(
                    [
                        {
                            "displayName": "master",
                            "description": "the master Jenkins node",
                            "temporarilyOffline": False,
                            "monitorData": {
                                "hudson.node_monitors.SwapSpaceMonitor": {
                                    "totalPhysicalMemory": 67429359616,
                                    "availableSwapSpace": 59097583616,
                                    "_class": "hudson.node_monitors.SwapSpaceMonitor$MemoryUsage2",
                                    "availablePhysicalMemory": 4450242560,
                                    "totalSwapSpace": 64000876544,
                                },
                                "hudson.node_monitors.ClockMonitor": {
                                    "diff": 0,
                                    "_class": "hudson.util.ClockDifference",
                                },
                                "hudson.node_monitors.DiskSpaceMonitor": {
                                    "size": 290845855744,
                                    "timestamp": 1573468791686,
                                    "_class": "hudson.node_monitors.DiskSpaceMonitorDescriptor$DiskSpace",
                                    "path": "/var/lib/jenkins",
                                },
                                "hudson.node_monitors.TemporarySpaceMonitor": {
                                    "size": 32569888768,
                                    "timestamp": 1573468792277,
                                    "_class": "hudson.node_monitors.DiskSpaceMonitorDescriptor$DiskSpace",
                                    "path": "/tmp",
                                },
                                "hudson.node_monitors.ResponseTimeMonitor": {
                                    "timestamp": 1573468791687,
                                    "average": 0,
                                    "_class": "hudson.node_monitors.ResponseTimeMonitor$Data",
                                },
                                "hudson.node_monitors.ArchitectureMonitor": "MYARCH1",
                            },
                            "assignedLabels": [
                                {
                                    "busyExecutors": 3,
                                    "idleExecutors": 17,
                                    "nodes": [
                                        {"_class": "hudson.model.Hudson", "mode": "EXCLUSIVE"}
                                    ],
                                },
                                {"busyExecutors": 3, "idleExecutors": 17},
                            ],
                            "numExecutors": 20,
                            "idle": False,
                            "offlineCause": None,
                            "offline": False,
                            "_class": "hudson.model.Hudson$MasterComputer",
                            "jnlpAgent": False,
                        },
                        {
                            "displayName": "Windows",
                            "description": "Name: MYNAME, IP-Address: 1.1.1.1",
                            "temporarilyOffline": False,
                            "monitorData": {
                                "hudson.node_monitors.SwapSpaceMonitor": {
                                    "totalPhysicalMemory": 17179332608,
                                    "availableSwapSpace": 8569982976,
                                    "_class": "hudson.node_monitors.SwapSpaceMonitor$MemoryUsage2",
                                    "availablePhysicalMemory": 5656227840,
                                    "totalSwapSpace": 22548041728,
                                },
                                "hudson.node_monitors.ClockMonitor": {
                                    "diff": 8,
                                    "_class": "hudson.util.ClockDifference",
                                },
                                "hudson.node_monitors.DiskSpaceMonitor": {
                                    "size": 15085674496,
                                    "timestamp": 1573468791711,
                                    "_class": "hudson.node_monitors.DiskSpaceMonitorDescriptor$DiskSpace",
                                    "path": "C:\\\\",
                                },
                                "hudson.node_monitors.TemporarySpaceMonitor": {
                                    "size": 15085674496,
                                    "timestamp": 1573468792334,
                                    "_class": "hudson.node_monitors.DiskSpaceMonitorDescriptor$DiskSpace",
                                    "path": "C:\\\\Windows\\\\Temp",
                                },
                                "hudson.node_monitors.ResponseTimeMonitor": {
                                    "timestamp": 1573468791722,
                                    "average": 35,
                                    "_class": "hudson.node_monitors.ResponseTimeMonitor$Data",
                                },
                                "hudson.node_monitors.ArchitectureMonitor": "MYARCH",
                            },
                            "assignedLabels": [
                                {
                                    "busyExecutors": 0,
                                    "idleExecutors": 1,
                                    "nodes": [
                                        {"_class": "hudson.slaves.DumbSlave", "mode": "EXCLUSIVE"}
                                    ],
                                },
                                {"busyExecutors": 0, "idleExecutors": 1},
                            ],
                            "numExecutors": 1,
                            "idle": True,
                            "offlineCause": None,
                            "offline": False,
                            "_class": "hudson.slaves.SlaveComputer",
                            "jnlpAgent": True,
                        },
                        {
                            "displayName": "foo",
                            "description": "Name: MYNAME, IP-Address: 1.1.1.1",
                            "temporarilyOffline": False,
                            "monitorData": {
                                "hudson.node_monitors.SwapSpaceMonitor": {
                                    "totalPhysicalMemory": 17179332608,
                                    "availableSwapSpace": 8569982976,
                                    "_class": "hudson.node_monitors.SwapSpaceMonitor$MemoryUsage2",
                                    "availablePhysicalMemory": 5656227840,
                                    "totalSwapSpace": 22548041728,
                                },
                                "hudson.node_monitors.ClockMonitor": {
                                    "diff": -5000,
                                    "_class": "hudson.util.ClockDifference",
                                },
                                "hudson.node_monitors.DiskSpaceMonitor": {
                                    "size": 15085674496,
                                    "timestamp": 1573468791711,
                                    "_class": "hudson.node_monitors.DiskSpaceMonitorDescriptor$DiskSpace",
                                    "path": "C:\\\\",
                                },
                                "hudson.node_monitors.TemporarySpaceMonitor": {
                                    "size": 15085674496,
                                    "timestamp": 1573468792334,
                                    "_class": "hudson.node_monitors.DiskSpaceMonitorDescriptor$DiskSpace",
                                    "path": "C:\\\\Windows\\\\Temp",
                                },
                                "hudson.node_monitors.ResponseTimeMonitor": {
                                    "timestamp": 1573468791722,
                                    "average": 1337,
                                    "_class": "hudson.node_monitors.ResponseTimeMonitor$Data",
                                },
                                "hudson.node_monitors.ArchitectureMonitor": "MYARCH",
                            },
                            "assignedLabels": [
                                {
                                    "name": "fra",
                                    "busyExecutors": 0,
                                    "idleExecutors": 1,
                                    "nodes": [
                                        {"_class": "hudson.slaves.DumbSlave", "mode": "EXCLUSIVE"}
                                    ],
                                },
                                {
                                    "name": "ber",
                                    "busyExecutors": 0,
                                    "idleExecutors": 1,
                                },
                            ],
                            "numExecutors": 1,
                            "idle": True,
                            "offlineCause": None,
                            "offline": False,
                            "_class": "hudson.slaves.SlaveComputer",
                            "jnlpAgent": True,
                        },
                    ]
                )
            ]
        ]
    )


def test_discovery(section: Section) -> None:
    value = list(discover_jenkins_nodes(section))
    expected = [
        Service(item="master"),
        Service(item="Windows"),
        Service(
            item="foo",
            labels=[
                ServiceLabel("cmk/jenkins_node_label_fra", "yes"),
                ServiceLabel("cmk/jenkins_node_label_ber", "yes"),
            ],
        ),
    ]
    assert value == expected


def test_check_windows_item(section: Section) -> None:
    value = list(check_jenkins_nodes("Windows", CHECK_DEFAULT_PARAMETERS, section))
    expected = [
        Result(state=State.OK, summary="Description: Name: Myname, Ip-Address: 1.1.1.1"),
        Result(state=State.OK, summary="Is JNLP agent: yes"),
        Result(state=State.OK, summary="Is idle: yes"),
        Result(state=State.OK, summary="Total number of executors: 1"),
        Metric("jenkins_num_executors", 1),
        Result(state=State.OK, summary="Number of busy executors: 0"),
        Metric("jenkins_busy_executors", 0),
        Result(state=State.OK, summary="Number of idle executors: 1"),
        Metric("jenkins_idle_executors", 1),
        Result(state=State.OK, summary="Mode: Exclusive"),
        Result(state=State.OK, summary="Offline: no"),
        Result(state=State.OK, summary="Average response time: 35 milliseconds"),
        Metric("avg_response_time", 0.035),
        Result(state=State.OK, summary="Clock difference: 8 milliseconds"),
        Metric("jenkins_clock", 0.008),
        Result(state=State.OK, summary="Free temp space: 14.0 GiB"),
        Metric("jenkins_temp", 15085674496),
    ]
    assert value == expected


def test_check_master_item(section: Section) -> None:
    value = list(check_jenkins_nodes("master", CHECK_DEFAULT_PARAMETERS, section))
    expected = [
        Result(state=State.OK, summary="Description: The Master Jenkins Node"),
        Result(state=State.OK, summary="Is JNLP agent: no"),
        Result(state=State.OK, summary="Is idle: no"),
        Result(state=State.OK, summary="Total number of executors: 20"),
        Metric("jenkins_num_executors", 20),
        Result(state=State.OK, summary="Number of busy executors: 3"),
        Metric("jenkins_busy_executors", 3),
        Result(state=State.OK, summary="Number of idle executors: 17"),
        Metric("jenkins_idle_executors", 17),
        Result(state=State.OK, summary="Mode: Exclusive"),
        Result(state=State.OK, summary="Offline: no"),
        Result(state=State.OK, summary="Average response time: 0 seconds"),
        Metric("avg_response_time", 0.0),
        Result(state=State.OK, summary="Clock difference: 0 seconds"),
        Metric("jenkins_clock", 0.0),
        Result(state=State.OK, summary="Free temp space: 30.3 GiB"),
        Metric("jenkins_temp", 32569888768),
    ]
    assert value == expected


def test_check_foo_item(section: Section) -> None:
    item = "foo"
    params = {
        **CHECK_DEFAULT_PARAMETERS,
        "avg_response_time": ("fixed", (1.0, 2.0)),
        "jenkins_clock": ("fixed", (3.0, 4.0)),
    }

    value = list(check_jenkins_nodes(item, params, section))
    expected = [
        Result(state=State.OK, summary="Description: Name: Myname, Ip-Address: 1.1.1.1"),
        Result(state=State.OK, summary="Is JNLP agent: yes"),
        Result(state=State.OK, summary="Is idle: yes"),
        Result(state=State.OK, summary="Total number of executors: 1"),
        Metric("jenkins_num_executors", 1),
        Result(state=State.OK, summary="Number of busy executors: 0"),
        Metric("jenkins_busy_executors", 0),
        Result(state=State.OK, summary="Number of idle executors: 1"),
        Metric("jenkins_idle_executors", 1),
        Result(state=State.OK, summary="Mode: Exclusive (Labels: fra ber)"),
        Result(state=State.OK, summary="Offline: no"),
        Result(
            state=State.WARN,
            summary="Average response time: 1 second (warn/crit at 1 second/2 seconds)",
        ),
        Metric("avg_response_time", 1.337, levels=(1.0, 2.0)),
        Result(
            state=State.CRIT,
            summary="Clock difference: 5 seconds (warn/crit at 3 seconds/4 seconds)",
        ),
        Metric("jenkins_clock", 5.000, levels=(3.0, 4.0)),
        Result(state=State.OK, summary="Free temp space: 14.0 GiB"),
        Metric("jenkins_temp", 15085674496),
    ]

    assert value == expected


@pytest.fixture(scope="module", name="multi_label_section")
def _multi_label_section() -> Section:
    """
    Example output containing a node with multiple assigned labels
    """
    return parse_jenkins_nodes(
        [
            [
                json.dumps(
                    [
                        {
                            "_class": "hudson.slaves.SlaveComputer",
                            "assignedLabels": [
                                {
                                    "busyExecutors": 42,
                                    "idleExecutors": 63,
                                    "name": "fra",
                                    "nodes": [
                                        {"mode": "EXCLUSIVE"},
                                        {"mode": "EXCLUSIVE"},
                                        {"mode": "NORMAL"},
                                        {"mode": "EXCLUSIVE"},
                                        {"mode": "EXCLUSIVE"},
                                    ],
                                },
                                {
                                    "busyExecutors": 7,
                                    "idleExecutors": 14,
                                    "name": "build-fra-002.lan.corpo.net",
                                    "nodes": [{"mode": "NORMAL"}],
                                },
                                {
                                    "busyExecutors": 42,
                                    "idleExecutors": 63,
                                    "name": "both",
                                    "nodes": [
                                        {"mode": "EXCLUSIVE"},
                                        {"mode": "EXCLUSIVE"},
                                        {"mode": "EXCLUSIVE"},
                                        {"mode": "NORMAL"},
                                        {"mode": "EXCLUSIVE"},
                                    ],
                                },
                            ],
                            "description": "",
                            "displayName": "build-fra-002.lan.corpo.net",
                            "idle": False,
                            "jnlpAgent": False,
                            "monitorData": {},
                            "numExecutors": 21,
                            "offline": False,
                            "offlineCause": None,
                            "temporarilyOffline": False,
                        }
                    ]
                )
            ]
        ]
    )


def test_showing_correct_executor_amount(multi_label_section: Section) -> None:
    """
    Test that the correct executor amount is shown

    The test will only check for very specific metrics and their correct value.
    """
    item = "build-fra-002.lan.corpo.net"

    value = set(check_jenkins_nodes(item, CHECK_DEFAULT_PARAMETERS, multi_label_section))
    expected = {
        Metric("jenkins_num_executors", 21.0),
        Metric("jenkins_busy_executors", 7.0),
        Metric("jenkins_idle_executors", 14.0),
    }

    assert value & expected == expected


def test_showing_correct_executor_mode(multi_label_section: Section) -> None:
    item = "build-fra-002.lan.corpo.net"

    value = check_jenkins_nodes(item, CHECK_DEFAULT_PARAMETERS, multi_label_section)
    expected = Result(state=State.OK, summary="Mode: Normal")

    assert expected in value
