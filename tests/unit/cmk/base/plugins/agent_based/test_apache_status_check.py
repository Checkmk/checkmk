#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict

import pytest

from cmk.base.plugins.agent_based import apache_status
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


def make_agent_output_1():
    return [
        ["127.0.0.1", "None", "127.0.0.1"],
        ["127.0.0.1", "None", "ServerVersion:", "Apache/2.4.29", "(Ubuntu)"],
        ["127.0.0.1", "None", "ServerMPM:", "event"],
        ["127.0.0.1", "None", "Server", "Built:", "2019-07-16T18:14:45"],
        ["127.0.0.1", "None", "CurrentTime:", "Wednesday,", "14-Aug-2019", "10:46:26", "CEST"],
        ["127.0.0.1", "None", "RestartTime:", "Monday,", "12-Aug-2019", "11:28:34", "CEST"],
        ["127.0.0.1", "None", "ParentServerConfigGeneration:", "9"],
        ["127.0.0.1", "None", "ParentServerMPMGeneration:", "8"],
        ["127.0.0.1", "None", "ServerUptimeSeconds:", "170272"],
        [
            "127.0.0.1",
            "None",
            "ServerUptime:",
            "1",
            "day",
            "23",
            "hours",
            "17",
            "minutes",
            "52",
            "seconds",
        ],
        ["127.0.0.1", "None", "Load1:", "0.70"],
        ["127.0.0.1", "None", "Load5:", "0.66"],
        ["127.0.0.1", "None", "Load15:", "0.67"],
        ["127.0.0.1", "None", "Total", "Accesses:", "64265"],
        ["127.0.0.1", "None", "Total", "kBytes:", "105614"],
        ["127.0.0.1", "None", "CPUUser:", ".34"],
        ["127.0.0.1", "None", "CPUSystem:", ".15"],
        ["127.0.0.1", "None", "CPUChildrenUser:", "0"],
        ["127.0.0.1", "None", "CPUChildrenSystem:", "0"],
        ["127.0.0.1", "None", "CPULoad:", ".000287775"],
        ["127.0.0.1", "None", "Uptime:", "170272"],
        ["127.0.0.1", "None", "ReqPerSec:", ".377426"],
        ["127.0.0.1", "None", "BytesPerSec:", "635.153"],
        ["127.0.0.1", "None", "BytesPerReq:", "1682.86"],
        ["127.0.0.1", "None", "BusyWorkers:", "1"],
        ["127.0.0.1", "None", "IdleWorkers:", "49"],
        ["127.0.0.1", "None", "ConnsTotal:", "1"],
        ["127.0.0.1", "None", "ConnsAsyncWriting:", "0"],
        ["127.0.0.1", "None", "ConnsAsyncKeepAlive:", "0"],
        ["127.0.0.1", "None", "ConnsAsyncClosing:", "0"],
        [
            "127.0.0.1",
            "None",
            "Scoreboard:",
            "__________________________________W_______________....................................................................................................",
        ],
    ]


def make_section_1():
    return {
        "127.0.0.1": {
            "BusyWorkers": 1,
            "BytesPerReq": 1682.86,
            "BytesPerSec": 635.153,
            "CPULoad": 0.000287775,
            "ConnsAsyncClosing": 0,
            "ConnsAsyncKeepAlive": 0,
            "ConnsAsyncWriting": 0,
            "ConnsTotal": 1,
            "IdleWorkers": 49,
            "OpenSlots": 100,
            "ReqPerSec": 0.377426,
            "Scoreboard": (
                "__________________________________W_______________"
                ".................................................."
                ".................................................."
            ),
            "State_Closing": 0,
            "State_DNS": 0,
            "State_Finishing": 0,
            "State_IdleCleanup": 0,
            "State_Keepalive": 0,
            "State_Logging": 0,
            "State_ReadingRequest": 0,
            "State_SendingReply": 1,
            "State_StartingUp": 0,
            "State_Waiting": 49,
            "Total Accesses": 64265,
            "Total kBytes": 105614.0,
            "TotalSlots": 150,
            "Uptime": 170272,
        },
    }


def make_agent_output_2():
    return [
        ["127.0.0.1", "None", "MY CHECK MK", "127.0.0.1"],
        ["127.0.0.1", "None", "MY CHECK MK", "ServerVersion: Apache/2.4.29 (Ubuntu)"],
        ["127.0.0.1", "None", "MY CHECK MK", "ServerMPM: event"],
        ["127.0.0.1", "None", "MY CHECK MK", "Server Built: 2019-07-16T18:14:45"],
        ["127.0.0.1", "None", "MY CHECK MK", "CurrentTime: Tuesday, 13-Aug-2019 15:10:54 CEST"],
        ["127.0.0.1", "None", "MY CHECK MK", "RestartTime: Monday, 12-Aug-2019 11:28:34 CEST"],
        ["127.0.0.1", "None", "MY CHECK MK", "ParentServerConfigGeneration: 6"],
        ["127.0.0.1", "None", "MY CHECK MK", "ParentServerMPMGeneration: 5"],
        ["127.0.0.1", "None", "MY CHECK MK", "ServerUptimeSeconds: 99739"],
        ["127.0.0.1", "None", "MY CHECK MK", "ServerUptime: 1 day 3 hours 42 minutes 19 seconds"],
        ["127.0.0.1", "None", "MY CHECK MK", "Load1: 0.70"],
        ["127.0.0.1", "None", "MY CHECK MK", "Load5: 0.70"],
        ["127.0.0.1", "None", "MY CHECK MK", "Load15: 0.58"],
        ["127.0.0.1", "None", "MY CHECK MK", "Total Accesses: 62878"],
        ["127.0.0.1", "None", "MY CHECK MK", "Total kBytes: 101770"],
        ["127.0.0.1", "None", "MY CHECK MK", "CPUUser: 2.99"],
        ["127.0.0.1", "None", "MY CHECK MK", "CPUSystem: 1.82"],
        ["127.0.0.1", "None", "MY CHECK MK", "CPUChildrenUser: 0"],
        ["127.0.0.1", "None", "MY CHECK MK", "CPUChildrenSystem: 0"],
        ["127.0.0.1", "None", "MY CHECK MK", "CPULoad: .00482259"],
        ["127.0.0.1", "None", "MY CHECK MK", "Uptime: 99739"],
        ["127.0.0.1", "None", "MY CHECK MK", "ReqPerSec: .630425"],
        ["127.0.0.1", "None", "MY CHECK MK", "BytesPerSec: 1044.85"],
        ["127.0.0.1", "None", "MY CHECK MK", "BytesPerReq: 1657.38"],
        ["127.0.0.1", "None", "MY CHECK MK", "BusyWorkers: 1"],
        ["127.0.0.1", "None", "MY CHECK MK", "IdleWorkers: 49"],
        ["127.0.0.1", "None", "MY CHECK MK", "ConnsTotal: 0"],
        ["127.0.0.1", "None", "MY CHECK MK", "ConnsAsyncWriting: 0"],
        ["127.0.0.1", "None", "MY CHECK MK", "ConnsAsyncKeepAlive: 0"],
        ["127.0.0.1", "None", "MY CHECK MK", "ConnsAsyncClosing: 0"],
        [
            "127.0.0.1",
            "None",
            "MY CHECK MK",
            "Scoreboard: ________________________________W_________________....................................................................................................",
        ],
    ]


def make_section_2() -> Dict[str, Dict[str, float]]:
    return {
        "MY CHECK MK": {
            "BusyWorkers": 1,
            "BytesPerReq": 1657.38,
            "BytesPerSec": 1044.85,
            "CPULoad": 0.00482259,
            "ConnsAsyncClosing": 0,
            "ConnsAsyncKeepAlive": 0,
            "ConnsAsyncWriting": 0,
            "ConnsTotal": 0,
            "IdleWorkers": 49,
            "OpenSlots": 100,
            "ReqPerSec": 0.630425,
            "Scoreboard": (  # type: ignore[dict-item]
                " ________________________________W_________________"
                "..................................................."
                "................................................."
            ),
            "State_Closing": 0,
            "State_DNS": 0,
            "State_Finishing": 0,
            "State_IdleCleanup": 0,
            "State_Keepalive": 0,
            "State_Logging": 0,
            "State_ReadingRequest": 0,
            "State_SendingReply": 1,
            "State_StartingUp": 0,
            "State_Waiting": 49,
            "Total Accesses": 62878,
            "Total kBytes": 101770.0,
            "TotalSlots": 150,
            "Uptime": 99739,
        },
    }


@pytest.mark.parametrize(
    "string_table, section",
    [
        (make_agent_output_1(), make_section_1()),
        (make_agent_output_2(), make_section_2()),
    ],
)
def test_parse_function(string_table, section) -> None:
    assert apache_status.apache_status_parse(string_table) == section


def test_discovery() -> None:
    assert list(apache_status.discover_apache_status(make_section_2())) == [
        Service(item="MY CHECK MK"),
    ]


def test_check_function(monkeypatch) -> None:
    monkeypatch.setattr(
        apache_status,
        "get_value_store",
        lambda: {
            "apache_status_MY CHECK MK_accesses": (0, 62878),
            "apache_status_MY CHECK MK_bytes": (0, 104212480.0),
        },
    )

    assert list(apache_status.check_apache_status("MY CHECK MK", {}, make_section_2())) == [
        Result(state=State.OK, summary="Uptime: 1 day 3 hours"),
        Metric("Uptime", 99739),
        Result(state=State.OK, summary="Idle workers: 49"),
        Metric("IdleWorkers", 49),
        Result(state=State.OK, summary="Busy workers: 1"),
        Metric("BusyWorkers", 1),
        Result(state=State.OK, summary="Total slots: 150"),
        Metric("TotalSlots", 150),
        Result(state=State.OK, notice="Open slots: 100"),
        Metric("OpenSlots", 100),
        Result(state=State.OK, notice="CPU load: 0.00"),
        Metric("CPULoad", 0.00482259),
        Result(state=State.OK, notice="Requests per second: 0.00"),
        Metric("ReqPerSec", 0.0),
        Result(state=State.OK, notice="Bytes per request: 1657.38"),
        Metric("BytesPerReq", 1657.38),
        Result(state=State.OK, notice="Bytes per second: 0.00"),
        Metric("BytesPerSec", 0.0),
        Result(state=State.OK, notice="Total connections: 0"),
        Metric("ConnsTotal", 0),
        Result(state=State.OK, notice="Async writing connections: 0"),
        Metric("ConnsAsyncWriting", 0),
        Result(state=State.OK, notice="Async keep alive connections: 0"),
        Metric("ConnsAsyncKeepAlive", 0),
        Result(state=State.OK, notice="Async closing connections: 0"),
        Metric("ConnsAsyncClosing", 0),
        Metric("State_Waiting", 49),
        Metric("State_StartingUp", 0),
        Metric("State_ReadingRequest", 0),
        Metric("State_SendingReply", 1),
        Metric("State_Keepalive", 0),
        Metric("State_DNS", 0),
        Metric("State_Closing", 0),
        Metric("State_Logging", 0),
        Metric("State_Finishing", 0),
        Metric("State_IdleCleanup", 0),
        Result(state=State.OK, notice=("Scoreboard states:\n  Waiting: 49\n  SendingReply: 1")),
    ]
