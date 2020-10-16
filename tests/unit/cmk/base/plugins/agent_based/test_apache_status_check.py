#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

import cmk.base.plugins.agent_based.agent_based_api.v1
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_value_store,
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based import apache_status

AGENT_OUTPUT_1 = [
    [u'127.0.0.1', u'None', u'127.0.0.1'],
    [u'127.0.0.1', u'None', u'ServerVersion:', u'Apache/2.4.29', u'(Ubuntu)'],
    [u'127.0.0.1', u'None', u'ServerMPM:', u'event'],
    [u'127.0.0.1', u'None', u'Server', u'Built:', u'2019-07-16T18:14:45'],
    [u'127.0.0.1', u'None', u'CurrentTime:', u'Wednesday,', u'14-Aug-2019', u'10:46:26', u'CEST'],
    [u'127.0.0.1', u'None', u'RestartTime:', u'Monday,', u'12-Aug-2019', u'11:28:34', u'CEST'],
    [u'127.0.0.1', u'None', u'ParentServerConfigGeneration:', u'9'],
    [u'127.0.0.1', u'None', u'ParentServerMPMGeneration:', u'8'],
    [u'127.0.0.1', u'None', u'ServerUptimeSeconds:', u'170272'],
    [
        u'127.0.0.1', u'None', u'ServerUptime:', u'1', u'day', u'23', u'hours', u'17', u'minutes',
        u'52', u'seconds'
    ], [u'127.0.0.1', u'None', u'Load1:', u'0.70'], [u'127.0.0.1', u'None', u'Load5:', u'0.66'],
    [u'127.0.0.1', u'None', u'Load15:', u'0.67'],
    [u'127.0.0.1', u'None', u'Total', u'Accesses:', u'64265'],
    [u'127.0.0.1', u'None', u'Total', u'kBytes:', u'105614'],
    [u'127.0.0.1', u'None', u'CPUUser:', u'.34'], [u'127.0.0.1', u'None', u'CPUSystem:', u'.15'],
    [u'127.0.0.1', u'None', u'CPUChildrenUser:', u'0'],
    [u'127.0.0.1', u'None', u'CPUChildrenSystem:', u'0'],
    [u'127.0.0.1', u'None', u'CPULoad:', u'.000287775'],
    [u'127.0.0.1', u'None', u'Uptime:', u'170272'],
    [u'127.0.0.1', u'None', u'ReqPerSec:', u'.377426'],
    [u'127.0.0.1', u'None', u'BytesPerSec:', u'635.153'],
    [u'127.0.0.1', u'None', u'BytesPerReq:', u'1682.86'],
    [u'127.0.0.1', u'None', u'BusyWorkers:', u'1'], [u'127.0.0.1', u'None', u'IdleWorkers:', u'49'],
    [u'127.0.0.1', u'None', u'ConnsTotal:', u'1'],
    [u'127.0.0.1', u'None', u'ConnsAsyncWriting:', u'0'],
    [u'127.0.0.1', u'None', u'ConnsAsyncKeepAlive:', u'0'],
    [u'127.0.0.1', u'None', u'ConnsAsyncClosing:', u'0'],
    [
        u'127.0.0.1', u'None', u'Scoreboard:',
        u'__________________________________W_______________....................................................................................................'
    ]
]

SECTION_1 = {
    '127.0.0.1': {
        'BusyWorkers': 1,
        'BytesPerReq': 1682.86,
        'BytesPerSec': 635.153,
        'CPULoad': 0.000287775,
        'ConnsAsyncClosing': 0,
        'ConnsAsyncKeepAlive': 0,
        'ConnsAsyncWriting': 0,
        'ConnsTotal': 1,
        'IdleWorkers': 49,
        'OpenSlots': 100,
        'ReqPerSec': 0.377426,
        'Scoreboard': ('__________________________________W_______________'
                       '..................................................'
                       '..................................................'),
        'State_Closing': 0,
        'State_DNS': 0,
        'State_Finishing': 0,
        'State_IdleCleanup': 0,
        'State_Keepalive': 0,
        'State_Logging': 0,
        'State_ReadingRequest': 0,
        'State_SendingReply': 1,
        'State_StartingUp': 0,
        'State_Waiting': 49,
        'Total Accesses': 64265,
        'Total kBytes': 105614.0,
        'TotalSlots': 150,
        'Uptime': 170272,
    },
}

AGENT_OUTPUT_2 = [
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'127.0.0.1'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ServerVersion: Apache/2.4.29 (Ubuntu)'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ServerMPM: event'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Server Built: 2019-07-16T18:14:45'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CurrentTime: Tuesday, 13-Aug-2019 15:10:54 CEST'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'RestartTime: Monday, 12-Aug-2019 11:28:34 CEST'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ParentServerConfigGeneration: 6'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ParentServerMPMGeneration: 5'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ServerUptimeSeconds: 99739'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ServerUptime: 1 day 3 hours 42 minutes 19 seconds'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Load1: 0.70'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Load5: 0.70'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Load15: 0.58'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Total Accesses: 62878'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Total kBytes: 101770'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CPUUser: 2.99'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CPUSystem: 1.82'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CPUChildrenUser: 0'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CPUChildrenSystem: 0'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CPULoad: .00482259'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Uptime: 99739'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ReqPerSec: .630425'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'BytesPerSec: 1044.85'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'BytesPerReq: 1657.38'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'BusyWorkers: 1'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'IdleWorkers: 49'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ConnsTotal: 0'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ConnsAsyncWriting: 0'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ConnsAsyncKeepAlive: 0'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ConnsAsyncClosing: 0'],
    [
        u'127.0.0.1', u'None', u'MY CHECK MK',
        u'Scoreboard: ________________________________W_________________....................................................................................................'
    ]
]

SECTION_2 = {
    'MY CHECK MK': {
        'BusyWorkers': 1,
        'BytesPerReq': 1657.38,
        'BytesPerSec': 1044.85,
        'CPULoad': 0.00482259,
        'ConnsAsyncClosing': 0,
        'ConnsAsyncKeepAlive': 0,
        'ConnsAsyncWriting': 0,
        'ConnsTotal': 0,
        'IdleWorkers': 49,
        'OpenSlots': 100,
        'ReqPerSec': 0.630425,
        'Scoreboard': (' ________________________________W_________________'
                       '...................................................'
                       '.................................................'),
        'State_Closing': 0,
        'State_DNS': 0,
        'State_Finishing': 0,
        'State_IdleCleanup': 0,
        'State_Keepalive': 0,
        'State_Logging': 0,
        'State_ReadingRequest': 0,
        'State_SendingReply': 1,
        'State_StartingUp': 0,
        'State_Waiting': 49,
        'Total Accesses': 62878,
        'Total kBytes': 101770.0,
        'TotalSlots': 150,
        'Uptime': 99739,
    },
}


@pytest.mark.parametrize("string_table, section", [
    (AGENT_OUTPUT_1, SECTION_1),
    (AGENT_OUTPUT_2, SECTION_2),
])
def test_parse_function(string_table, section):
    assert apache_status.apache_status_parse(string_table) == section


def test_discovery():
    assert list(apache_status.discover_apache_status(SECTION_2)) == [
        Service(item='MY CHECK MK'),
    ]


def test_check_function(monkeypatch):
    monkeypatch.setattr(
        apache_status,
        "get_value_store",
        lambda: {
            'apache_status_MY CHECK MK_accesses': (0, 62878),
            'apache_status_MY CHECK MK_bytes': (0, 104212480.0),
        },
    )

    assert list(apache_status.check_apache_status("MY CHECK MK", {}, SECTION_2)) == [
        Result(state=State.OK, summary='Uptime: 1 day 3 hours'),
        Metric('Uptime', 99739),
        Result(state=State.OK, summary='Idle workers: 49'),
        Metric('IdleWorkers', 49),
        Result(state=State.OK, summary='Busy workers: 1'),
        Metric('BusyWorkers', 1),
        Result(state=State.OK, summary='Total slots: 150'),
        Metric('TotalSlots', 150),
        Result(state=State.OK, summary='Open slots: 100'),
        Metric('OpenSlots', 100),
        Result(state=State.OK, summary='CPU load: 0.00'),
        Metric('CPULoad', 0.00482259),
        Result(state=State.OK, summary='Requests per second: 0.00'),
        Metric('ReqPerSec', 0.0),
        Result(state=State.OK, summary='Bytes per request: 1657.38'),
        Metric('BytesPerReq', 1657.38),
        Result(state=State.OK, summary='Bytes per second: 0.00'),
        Metric('BytesPerSec', 0.0),
        Result(state=State.OK, summary='Total connections: 0'),
        Metric('ConnsTotal', 0),
        Result(state=State.OK, summary='Async writing connections: 0'),
        Metric('ConnsAsyncWriting', 0),
        Result(state=State.OK, summary='Async keep alive connections: 0'),
        Metric('ConnsAsyncKeepAlive', 0),
        Result(state=State.OK, summary='Async closing connections: 0'),
        Metric('ConnsAsyncClosing', 0),
        Metric('State_Waiting', 49),
        Metric('State_StartingUp', 0),
        Metric('State_ReadingRequest', 0),
        Metric('State_SendingReply', 1),
        Metric('State_Keepalive', 0),
        Metric('State_DNS', 0),
        Metric('State_Closing', 0),
        Metric('State_Logging', 0),
        Metric('State_Finishing', 0),
        Metric('State_IdleCleanup', 0),
        Result(state=State.OK, notice=('Scoreboard states:\n  Waiting: 49\n  SendingReply: 1')),
    ]
