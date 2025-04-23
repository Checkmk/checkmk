#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.mknotifyd import (  # Queue,
    check_mknotifyd,
    check_mknotifyd_connection,
    check_mknotifyd_connection_v2,
    Connection,
    discover_mknotifyd,
    discover_mknotifyd_connection,
    discover_mknotifyd_connection_v2,
    MkNotifySection,
    parse_mknotifyd,
    Site,
    Spool,
)

# TODO: test outgoing connections + states

INFO_ERROR = [["1571212728"], ["[EX]"], ["Binary file (standard input) matches"]]
SECTION_ERROR = MkNotifySection(
    timestamp=1571212728.0,
    sites={"EX": Site(spools={}, connections={}, connections_v2={})},
)

INFO_STANDARD = [
    ["1571212728"],
    ["[heute]"],
    ["Version:         2019.10.14"],
    ["Updated:         1571212726 (2019-10-16 09:58:46)"],
    ["Started:         1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Configuration:   1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Listening FD:    5"],
    ["Spool:           New"],
    ["Count:           0"],
    ["Oldest:"],
    ["Youngest:"],
    ["Spool:           Deferred"],
    ["Count:           0"],
    ["Oldest:"],
    ["Youngest:"],
    ["Spool:           Corrupted"],
    ["Count:           0"],
    ["Oldest:"],
    ["Youngest:"],
    ["Queue:           mail"],
    ["Waiting:         0"],
    ["Processing:      0"],
    ["Queue:           None"],
    ["Waiting:         0"],
    ["Processing:      0"],
    ["Site:                     remote_site (127.0.0.1)"],
    ["Connection:               127.0.0.1:49850"],
    ["Type:                     incoming"],
    ["State:                    established"],
    ["Since:                    1571143941 (2019-10-15 14:52:21, 68785 sec ago)"],
    ["Connect Time:             30"],
    ["Notifications Sent:       47"],
    ["Notifications Received:   47"],
    ["Pending Acknowledgements:"],
    ["Socket FD:                6"],
    ["HB. Interval:             10 sec"],
    ["LastIncomingData:         1571212661 (2019-10-16 09:57:41, 65 sec ago)"],
    ["LastHeartbeat:            1571212717 (2019-10-16 09:58:37, 9 sec ago)"],
    ["InputBuffer:              0 Bytes"],
    ["OutputBuffer:             0 Bytes"],
]

SECTION_STANDARD = MkNotifySection(
    sites={
        "heute": Site(
            updated=1571212726,
            version="2019.10.14",
            connections={
                "127.0.0.1": Connection(
                    type_="incoming",
                    state="established",
                    since=1571143941,
                    notifications_sent=47,
                    notifications_received=47,
                    connect_time=30,
                ),
            },
            connections_v2={
                "remote_site": Connection(
                    type_="incoming",
                    state="established",
                    since=1571143941,
                    notifications_sent=47,
                    notifications_received=47,
                    connect_time=30,
                ),
            },
            spools={
                "Corrupted": Spool(count=0, oldest=None, youngest=None),
                "Deferred": Spool(count=0, oldest=None, youngest=None),
                "New": Spool(count=0, oldest=None, youngest=None),
            },
        ),
    },
    timestamp=1571212728.0,
)

INFO_CONNECTION_COOLDOWN = [
    ["1571212728"],
    ["[heute]"],
    ["Version:         2019.10.14"],
    ["Updated:         1571212726 (2019-10-16 09:58:46)"],
    ["Started:         1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Configuration:   1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Listening FD:    5"],
    ["Spool:           New"],
    ["Count:           0"],
    ["Oldest:"],
    ["Youngest:"],
    ["Spool:           Deferred"],
    ["Count:           0"],
    ["Oldest:"],
    ["Youngest:"],
    ["Spool:           Corrupted"],
    ["Count:           0"],
    ["Oldest:"],
    ["Youngest:"],
    ["Queue:           mail"],
    ["Waiting:         0"],
    ["Processing:      0"],
    ["Queue:           None"],
    ["Waiting:         0"],
    ["Processing:      0"],
    ["Site:                     remote_site (127.0.0.1)"],
    ["Connection:               127.0.0.1:49850"],
    ["Type:                     incoming"],
    ["State:                    cooldown"],
    ["Status Message:           All good"],
    ["Since:                    1571143941 (2019-10-15 14:52:21, 68785 sec ago)"],
    ["Notifications Sent:       0"],
    ["Notifications Received:   0"],
    ["Pending Acknowledgements:"],
    ["Socket FD:                6"],
    ["HB. Interval:             10 sec"],
    ["LastIncomingData:         1571212661 (2019-10-16 09:57:41, 65 sec ago)"],
    ["LastHeartbeat:            1571212717 (2019-10-16 09:58:37, 9 sec ago)"],
    ["InputBuffer:              0 Bytes"],
    ["OutputBuffer:             0 Bytes"],
]

SECTION_CONNECTION_COOLDOWN = MkNotifySection(
    sites={
        "heute": Site(
            updated=1571212726,
            version="2019.10.14",
            connections={
                "127.0.0.1": Connection(
                    type_="incoming",
                    state="cooldown",
                    status_message="All good",
                    since=1571143941,
                    notifications_sent=0,
                    notifications_received=0,
                ),
            },
            connections_v2={
                "remote_site": Connection(
                    type_="incoming",
                    state="cooldown",
                    status_message="All good",
                    since=1571143941,
                    notifications_sent=0,
                    notifications_received=0,
                ),
            },
            spools={
                "Corrupted": Spool(count=0, oldest=None, youngest=None),
                "Deferred": Spool(count=0, oldest=None, youngest=None),
                "New": Spool(count=0, oldest=None, youngest=None),
            },
        ),
    },
    timestamp=1571212728.0,
)

INFO_WITH_DEFERRED_CORRUPTED_NEW = [
    ["1571212738"],
    ["[heute]"],
    ["Version:         2019.10.14"],
    ["Updated:         1571212726 (2019-10-16 09:58:46)"],
    ["Started:         1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Configuration:   1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Listening FD:    5"],
    ["Spool:           New"],
    ["Count:           2"],
    ["Oldest:          1571212726 (2019-10-16 09:58:46)"],
    ["Youngest:        1571212726 (2019-10-16 09:58:46)"],
    ["Spool:           Deferred"],
    ["Count:           3"],
    ["Oldest:          1571212726 (2019-10-16 09:58:46)"],
    ["Youngest:        1571212726 (2019-10-16 09:58:46)"],
    ["Spool:           Corrupted"],
    ["Count:           1"],
    ["Oldest:          1571212726 (2019-10-16 09:58:46)"],
    ["Youngest:        1571212726 (2019-10-16 09:58:46)"],
    ["Queue:           mail"],
    ["Waiting:         0"],
    ["Processing:      0"],
    ["Queue:           None"],
    ["Waiting:         0"],
    ["Processing:      0"],
]
SECTION_WITH_DEFERRED_CORRUPTED_NEW = MkNotifySection(
    sites={
        "heute": Site(
            updated=1571212726,
            version="2019.10.14",
            connections={},
            connections_v2={},
            spools={
                "Corrupted": Spool(count=1, oldest=1571212726, youngest=1571212726),
                "Deferred": Spool(count=3, oldest=1571212726, youngest=1571212726),
                "New": Spool(count=2, oldest=1571212726, youngest=1571212726),
            },
        ),
    },
    timestamp=1571212738.0,
)

INFO_TIMESTAMP_PER_SITE = [
    ["1571212728"],
    ["[heute]"],
    ["Version:         2019.10.14"],
    ["Updated:         1571212726 (2019-10-16 09:58:46)"],
    ["Started:         1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Configuration:   1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Listening FD:    5"],
    ["1571212730"],
    ["[morgen]"],
    ["Version:         2019.10.14"],
    ["Updated:         1571212726 (2019-10-16 09:58:46)"],
    ["Started:         1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Configuration:   1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Listening FD:    5"],
]
SECTION_TIMESTAMP_PER_SITE = MkNotifySection(
    sites={
        "heute": Site(
            updated=1571212726,
            version="2019.10.14",
            spools={},
            connections={},
            connections_v2={},
        ),
        "morgen": Site(
            updated=1571212726,
            version="2019.10.14",
            spools={},
            connections={},
            connections_v2={},
        ),
    },
    timestamp=1571212728.0,
)


@pytest.mark.parametrize(
    "info, section",
    [
        pytest.param(INFO_ERROR, SECTION_ERROR),
        pytest.param(INFO_STANDARD, SECTION_STANDARD),
        pytest.param(INFO_WITH_DEFERRED_CORRUPTED_NEW, SECTION_WITH_DEFERRED_CORRUPTED_NEW),
        pytest.param(INFO_CONNECTION_COOLDOWN, SECTION_CONNECTION_COOLDOWN),
        pytest.param(INFO_TIMESTAMP_PER_SITE, SECTION_TIMESTAMP_PER_SITE),
    ],
)
def test_parse_mknotifyd(info: StringTable, section: MkNotifySection) -> None:
    with time_machine.travel(
        datetime.datetime.fromisoformat("2019-05-22T14:00:00").replace(tzinfo=ZoneInfo("UTC"))
    ):
        assert parse_mknotifyd(info) == section


@pytest.mark.parametrize(
    "section, services",
    [
        pytest.param(SECTION_ERROR, [Service(item="EX")]),
        pytest.param(SECTION_STANDARD, [Service(item="heute")]),
        pytest.param(SECTION_WITH_DEFERRED_CORRUPTED_NEW, [Service(item="heute")]),
        pytest.param(SECTION_CONNECTION_COOLDOWN, [Service(item="heute")]),
        pytest.param(SECTION_TIMESTAMP_PER_SITE, [Service(item="heute"), Service(item="morgen")]),
    ],
)
def test_discover_mknotifyd(section: MkNotifySection, services: Sequence[Service]) -> None:
    assert list(discover_mknotifyd(section)) == services


def test_discover_mknotifyd_connection_deprecated() -> None:
    assert not list(discover_mknotifyd_connection(SECTION_STANDARD))


@pytest.mark.parametrize(
    "section, services",
    [
        pytest.param(SECTION_ERROR, [], id="No connections"),
        pytest.param(
            SECTION_STANDARD,
            [Service(item="heute Notification Spooler connection to remote_site")],
            id="Connection discovered",
        ),
        pytest.param(
            SECTION_CONNECTION_COOLDOWN,
            [Service(item="heute Notification Spooler connection to remote_site")],
            id="Connection discovered",
        ),
    ],
)
def test_discover_mknotifyd_connection_v2(
    section: MkNotifySection, services: Sequence[Service]
) -> None:
    assert list(discover_mknotifyd_connection_v2(section)) == services


@pytest.mark.parametrize(
    "item, section, expected_output",
    [
        pytest.param(
            "EX",
            SECTION_ERROR,
            [
                Result(
                    state=State.CRIT,
                    summary="The state file seems to be empty or corrupted. It is very likely that the spooler is not working properly",
                )
            ],
            id="State file error",
        ),
        pytest.param(
            "heute",
            SECTION_STANDARD,
            [
                Result(
                    state=State.OK,
                    summary="Version: 2019.10.14",
                ),
                Result(
                    state=State.OK,
                    summary="Spooler running",
                ),
                Metric(name="last_updated", value=2),
                Metric(name="new_files", value=0),
            ],
            id="Normal section",
        ),
        pytest.param(
            "heute",
            SECTION_CONNECTION_COOLDOWN,
            [
                Result(
                    state=State.OK,
                    summary="Version: 2019.10.14",
                ),
                Result(
                    state=State.OK,
                    summary="Spooler running",
                ),
                Metric(name="last_updated", value=2),
                Metric(name="new_files", value=0),
            ],
            id="Normal section",
        ),
        pytest.param(
            "heute",
            SECTION_WITH_DEFERRED_CORRUPTED_NEW,
            [
                Result(
                    state=State.OK,
                    summary="Version: 2019.10.14",
                ),
                Result(
                    state=State.OK,
                    summary="Spooler running",
                ),
                Metric(name="last_updated", value=12),
                Metric(name="new_files", value=2),
                Result(state=State.WARN, summary="1 corrupted files: youngest 12 seconds ago"),
                Metric("corrupted_files", 1.0),
                Result(state=State.OK, summary="Deferred files: 3"),
                Metric("deferred_files", 3.0),
                Result(
                    state=State.WARN,
                    summary="Oldest: 12 seconds (warn/crit at 5 seconds/10 minutes 0 seconds)",
                ),
                Metric("deferred_age", 12.0, levels=(5.0, 600.0)),
            ],
            id="Section with deferred, corrupted, new",
        ),
    ],
)
def test_check_mknotifyd(
    item: str,
    expected_output: Sequence[object],
    section: MkNotifySection,
) -> None:
    assert list(check_mknotifyd(item, section)) == expected_output


@pytest.mark.parametrize(
    "item, section, expected_output",
    [
        pytest.param(
            "heute-127.0.0.1",
            SECTION_STANDARD,
            [
                Result(state=State.OK, summary="Alive"),
                Result(state=State.OK, summary="Uptime: 19 hours 6 minutes"),
                Result(state=State.OK, summary="Connect time: 30 seconds"),
                Result(state=State.OK, summary="Notifications sent: 47"),
                Result(state=State.OK, summary="Notifications received: 47"),
            ],
            id="old connection check, monitored but not discovered",
        ),
    ],
)
def test_check_mknotifyd_connection(
    item: str,
    expected_output: Sequence[object],
    section: MkNotifySection,
) -> None:
    assert list(check_mknotifyd_connection(item, section)) == expected_output


@pytest.mark.parametrize(
    "item, section, expected_output",
    [
        pytest.param(
            "heute Notification Spooler connection to remote_site",
            SECTION_STANDARD,
            [
                Result(state=State.OK, summary="Alive"),
                Result(state=State.OK, summary="Uptime: 19 hours 6 minutes"),
                Result(state=State.OK, summary="Connect time: 30 seconds"),
                Result(state=State.OK, summary="Notifications sent: 47"),
                Result(state=State.OK, summary="Notifications received: 47"),
            ],
            id="connection check",
        ),
        pytest.param(
            "heute Notification Spooler connection to remote_site",
            SECTION_CONNECTION_COOLDOWN,
            [
                Result(state=State.CRIT, summary="Connection failed or terminated"),
                Result(state=State.OK, summary="All good"),
            ],
            id="connection check",
        ),
        pytest.param(
            "heute Notification Spooler connection to remote_site",
            SECTION_WITH_DEFERRED_CORRUPTED_NEW,
            [],
            id="connection check with deferred, corrupted, new",
        ),
    ],
)
def test_check_mknotifyd_connection_v2(
    item: str,
    expected_output: Sequence[object],
    section: MkNotifySection,
) -> None:
    assert list(check_mknotifyd_connection_v2(item, section)) == expected_output
