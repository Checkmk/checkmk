#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.time.agent_based import timesyncd


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    store = dict[str, object]()
    monkeypatch.setattr(timesyncd, "get_value_store", lambda: store)


STRING_TABLE_STANDARD = [
    ["Server:", "91.189.91.157", "(ntp.ubuntu.com)"],
    ["Poll", "interval:", "32s", "(min:", "32s;", "max", "34min", "8s)"],
    ["Leap:", "normal"],
    ["Version:", "4"],
    ["Stratum:", "2"],
    ["Reference:", "C0248F97"],
    ["Precision:", "1us", "(-24)"],
    ["Root", "distance:", "87.096ms", "(max:", "5s)"],
    ["Offset:", "-53.991ms"],
    ["Delay:", "208.839ms"],
    ["Jitter:", "0"],
    ["Packet", "count:", "1"],
    ["Frequency:", "-500,000ppm"],
    ["[[[1569922392.37]]]"],
]
STRING_TABLE_LARGE_OFFSET = [
    ["Server:", "91.189.91.157", "(ntp.ubuntu.com)"],
    ["Poll", "interval:", "32s", "(min:", "32s;", "max", "34min", "8s)"],
    ["Leap:", "normal"],
    ["Version:", "4"],
    ["Stratum:", "2"],
    ["Reference:", "C0248F97"],
    ["Precision:", "1us", "(-24)"],
    ["Root", "distance:", "87.096ms", "(max:", "5s)"],
    [
        "Offset:",
        "-2y",
        "5M",
        "2w",
        "8d",
        "9h",
        "1min",
        "53.991us",
    ],
    ["Delay:", "208.839ms"],
    ["Jitter:", "0"],
    ["Packet", "count:", "1"],
    ["Frequency:", "-500,000ppm"],
    ["[[[1569922392.37]]]"],
]

# server cannot be reached
STRING_TABLE_NO_SERVER = [
    ["Server:", "(null)", "(ntp.ubuntu.com)"],
    ["Poll", "interval:", "0", "(min:", "32s;", "max", "34min", "8s)"],
    ["Packet", "count:", "0"],
    ["[[[1569922392.37]]]"],
]

# server is configured and can be resolved, but e.g. NTP blocked by firewall
STRING_TABLE_SERVER_NO_SYNC = [
    ["Server:", "10.200.0.1", "10.200.0.1"],
    ["Poll", "interval:", "34min 8s", "(min:", "32s;", "max", "34min", "8s)"],
    ["Packet", "count:", "0"],
    ["[[[1569922392.37]]]"],
]

STRING_TABLE_SERVER_NTP_MESSAGE = [
    [
        "NTPMessage={ Leap=0, Version=4, Mode=4, Stratum=2, Precision=-24, RootDelay=87.096ms, RootDispersion=26.397ms, Reference=C0248F97, OriginateTimestamp=Tue 2019-10-01 11:33:12 CEST, ReceiveTimestamp=Tue 2019-10-01 11:33:12 CEST, TransmitTimestamp=Tue 2019-10-01 11:33:12 CEST, DestinationTimestamp=Tue 2019-10-01 11:33:12 CEST, Ignored=no PacketCount=1, Jitter=0ms }"
    ],
    ["Timezone=Europe/Berlin"],
]

STRING_TABLE_NO_SYNC_NTP_MESSAGE = [
    ["Timezone=Europe/Berlin"],
]

STRING_TABLE_NTP_MESSAGE_NO_TIMEZONE = [
    [
        "NTPMessage={ Leap=0, Version=4, Mode=4, Stratum=2, Precision=-24, RootDelay=87.096ms, RootDispersion=26.397ms, Reference=C0248F97, OriginateTimestamp=Tue 2019-10-01 11:33:12 CEST, ReceiveTimestamp=Tue 2019-10-01 11:33:12 CEST, TransmitTimestamp=Tue 2019-10-01 11:33:12 CEST, DestinationTimestamp=Tue 2019-10-01 11:33:12 CEST, Ignored=no PacketCount=1, Jitter=0ms }"
    ],
]


@pytest.mark.parametrize(
    "string_table, string_table_ntpmessage,  result",
    [
        (STRING_TABLE_STANDARD, [], [Service()]),
        (STRING_TABLE_LARGE_OFFSET, [], [Service()]),
        (STRING_TABLE_NO_SERVER, STRING_TABLE_NO_SYNC_NTP_MESSAGE, [Service()]),
        (STRING_TABLE_SERVER_NO_SYNC, STRING_TABLE_NO_SYNC_NTP_MESSAGE, [Service()]),
        (STRING_TABLE_STANDARD, STRING_TABLE_SERVER_NTP_MESSAGE, [Service()]),
        (STRING_TABLE_STANDARD, STRING_TABLE_NTP_MESSAGE_NO_TIMEZONE, [Service()]),
        ([], [], []),
    ],
)
def test_discover_timesyncd(
    string_table: StringTable,
    string_table_ntpmessage: StringTable,
    result: DiscoveryResult,
) -> None:
    section = timesyncd.parse_timesyncd(string_table)
    section_ntpmessage = timesyncd.parse_timesyncd_ntpmessage(string_table_ntpmessage)
    assert list(timesyncd.discover_timesyncd(section, section_ntpmessage)) == result


@pytest.mark.usefixtures("empty_value_store")
@pytest.mark.parametrize(
    "string_table, string_table_ntpmessage, params, result",
    [
        (
            STRING_TABLE_STANDARD,
            [],
            timesyncd.default_check_parameters,
            [
                Result(state=State.OK, summary="Offset: 54 milliseconds"),
                Metric("time_offset", 0.053991, levels=(0.2, 0.5)),
                Result(
                    state=State.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=State.OK, summary="Stratum: 2.00"),
                Result(state=State.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
        ),
        (
            STRING_TABLE_LARGE_OFFSET,
            [],
            timesyncd.default_check_parameters,
            [
                Result(
                    state=State.CRIT,
                    summary="Offset: 2 years 175 days (warn/crit at 200 milliseconds/500 milliseconds)",
                ),
                Metric("time_offset", 78198540.000053991, levels=(0.2, 0.5)),
                Result(
                    state=State.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=State.OK, summary="Stratum: 2.00"),
                Result(state=State.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
        ),
        (
            STRING_TABLE_NO_SERVER,
            [],
            timesyncd.default_check_parameters,
            [
                Result(
                    state=State.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=State.CRIT, summary="Found no time server"),
            ],
        ),
        (
            STRING_TABLE_SERVER_NO_SYNC,
            [],
            timesyncd.default_check_parameters,
            [
                Result(
                    state=State.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=State.CRIT, summary="Found no time server"),
            ],
        ),
        (
            STRING_TABLE_STANDARD,
            STRING_TABLE_SERVER_NTP_MESSAGE,
            timesyncd.default_check_parameters,
            [
                Result(state=State.OK, summary="Offset: 54 milliseconds"),
                Metric("time_offset", 0.053991, levels=(0.2, 0.5)),
                Result(
                    state=State.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(
                    state=State.CRIT,
                    summary="Time since last NTPMessage: 22 hours 1 minute (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
                ),
                Metric("last_sync_receive_time", 79260.36999988556, levels=(3600.0, 7200.0)),
                Result(state=State.OK, summary="Stratum: 2.00"),
                Result(state=State.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
        ),
        (
            STRING_TABLE_STANDARD,
            STRING_TABLE_NTP_MESSAGE_NO_TIMEZONE,
            timesyncd.default_check_parameters,
            [
                Result(state=State.OK, summary="Offset: 54 milliseconds"),
                Metric("time_offset", 0.053991, levels=(0.2, 0.5)),
                Result(
                    state=State.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=State.OK, summary="Stratum: 2.00"),
                Result(state=State.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
        ),
    ],
)
def test_check_timesyncd_freeze(
    string_table: StringTable,
    string_table_ntpmessage: StringTable,
    params: timesyncd.CheckParams,
    result: CheckResult,
) -> None:
    server_time = 1569922392.37 + 60 * 60 * 22 + 60
    section = timesyncd.parse_timesyncd(string_table)
    section_ntpmessage = timesyncd.parse_timesyncd_ntpmessage(string_table_ntpmessage)
    with time_machine.travel(
        datetime.datetime.fromtimestamp(server_time, tz=ZoneInfo("UTC")), tick=False
    ):
        assert list(timesyncd.check_timesyncd(params, section, section_ntpmessage)) == result


@pytest.mark.usefixtures("empty_value_store")
@pytest.mark.parametrize(
    "string_table, string_table_ntpmessage, params, result",
    [
        (
            STRING_TABLE_NO_SERVER,
            [],
            timesyncd.default_check_parameters,
            [
                Result(
                    state=State.CRIT,
                    summary="Cannot reasonably calculate time since last synchronization (hosts time is running ahead)",
                ),
                Result(state=State.CRIT, summary="Found no time server"),
            ],
        ),
    ],
)
def test_check_timesyncd_negative_time(
    string_table: StringTable,
    string_table_ntpmessage: StringTable,
    params: timesyncd.CheckParams,
    result: CheckResult,
) -> None:
    wrong_server_time = 1569922392.37 - 60
    section = timesyncd.parse_timesyncd(string_table)
    section_ntpmessage = timesyncd.parse_timesyncd_ntpmessage(string_table_ntpmessage)
    with time_machine.travel(
        datetime.datetime.fromtimestamp(wrong_server_time, tz=ZoneInfo("UTC")), tick=False
    ):
        assert list(timesyncd.check_timesyncd(params, section, section_ntpmessage)) == result


def _string_table(offset: str, jitter: str, stratum: str, synced: bool = True) -> StringTable:
    """Agent output for the default-levels tests below, varying one value at a time."""
    table = [
        ["Server:", "91.189.91.157", "(ntp.ubuntu.com)"],
        ["Stratum:", stratum],
        ["Offset:", offset],
        ["Jitter:", jitter],
    ]
    if synced:
        table.append(["[[[1569922392.37]]]"])
    return table


@pytest.mark.usefixtures("empty_value_store")
@pytest.mark.parametrize(
    "string_table, result",
    [
        pytest.param(
            _string_table(offset="100ms", jitter="0", stratum="2"),
            [
                Result(state=State.OK, summary="Offset: 100 milliseconds"),
                Metric("time_offset", 0.1, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Time since last sync: 1 minute 0 seconds"),
                Metric("last_sync_time", 60.0),
                Result(state=State.OK, summary="Stratum: 2.00"),
                Result(state=State.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
            id="all levels OK",
        ),
        pytest.param(
            _string_table(offset="300ms", jitter="0", stratum="2"),
            [
                Result(
                    state=State.WARN,
                    summary="Offset: 300 milliseconds (warn/crit at 200 milliseconds/500 milliseconds)",
                ),
                Metric("time_offset", 0.3, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Time since last sync: 1 minute 0 seconds"),
                Metric("last_sync_time", 60.0),
                Result(state=State.OK, summary="Stratum: 2.00"),
                Result(state=State.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
            id="offset WARN",
        ),
        pytest.param(
            _string_table(offset="600ms", jitter="0", stratum="2"),
            [
                Result(
                    state=State.CRIT,
                    summary="Offset: 600 milliseconds (warn/crit at 200 milliseconds/500 milliseconds)",
                ),
                Metric("time_offset", 0.6, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Time since last sync: 1 minute 0 seconds"),
                Metric("last_sync_time", 60.0),
                Result(state=State.OK, summary="Stratum: 2.00"),
                Result(state=State.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
            id="offset CRIT",
        ),
        pytest.param(
            _string_table(offset="100ms", jitter="300ms", stratum="2"),
            [
                Result(state=State.OK, summary="Offset: 100 milliseconds"),
                Metric("time_offset", 0.1, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Time since last sync: 1 minute 0 seconds"),
                Metric("last_sync_time", 60.0),
                Result(state=State.OK, summary="Stratum: 2.00"),
                Result(
                    state=State.WARN,
                    summary="Jitter: 300 milliseconds (warn/crit at 200 milliseconds/500 milliseconds)",
                ),
                Metric("jitter", 0.3, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
            id="jitter WARN",
        ),
        pytest.param(
            _string_table(offset="100ms", jitter="600ms", stratum="2"),
            [
                Result(state=State.OK, summary="Offset: 100 milliseconds"),
                Metric("time_offset", 0.1, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Time since last sync: 1 minute 0 seconds"),
                Metric("last_sync_time", 60.0),
                Result(state=State.OK, summary="Stratum: 2.00"),
                Result(
                    state=State.CRIT,
                    summary="Jitter: 600 milliseconds (warn/crit at 200 milliseconds/500 milliseconds)",
                ),
                Metric("jitter", 0.6, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
            id="jitter CRIT",
        ),
        pytest.param(
            _string_table(offset="100ms", jitter="0", stratum="9"),
            [
                Result(state=State.OK, summary="Offset: 100 milliseconds"),
                Metric("time_offset", 0.1, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Time since last sync: 1 minute 0 seconds"),
                Metric("last_sync_time", 60.0),
                Result(state=State.CRIT, summary="Stratum: 9.00 (warn/crit at 9.00/9.00)"),
                Result(state=State.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
            id="stratum CRIT one below the configured level",
        ),
        pytest.param(
            _string_table(offset="100ms", jitter="0", stratum="10"),
            [
                Result(state=State.OK, summary="Offset: 100 milliseconds"),
                Metric("time_offset", 0.1, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Time since last sync: 1 minute 0 seconds"),
                Metric("last_sync_time", 60.0),
                Result(state=State.CRIT, summary="Stratum: 10.00 (warn/crit at 9.00/9.00)"),
                Result(state=State.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
            id="stratum CRIT at the configured level",
        ),
    ],
)
def test_check_timesyncd_default_levels(string_table: StringTable, result: CheckResult) -> None:
    """The default levels for offset, jitter and stratum yield OK, WARN and CRIT results.

    Stratum is the exception: its levels are built as warn == crit == configured value - 1,
    so it never WARNs and already goes CRIT one stratum below the configured value.
    """
    server_time = 1569922392.37 + 60
    section = timesyncd.parse_timesyncd(string_table)
    with time_machine.travel(
        datetime.datetime.fromtimestamp(server_time, tz=ZoneInfo("UTC")), tick=False
    ):
        assert (
            list(timesyncd.check_timesyncd(timesyncd.default_check_parameters, section, None))
            == result
        )


@pytest.mark.parametrize(
    "seconds_since_last_sync, sync_result",
    [
        pytest.param(
            60.0,
            [
                Result(state=State.OK, summary="Time since last sync: 1 minute 0 seconds"),
                Metric("last_sync_time", 60.0, levels=(300.0, 3600.0)),
            ],
            id="alert delay OK",
        ),
        pytest.param(
            600.0,
            [
                Result(
                    state=State.WARN,
                    summary="Time since last sync: 10 minutes 0 seconds "
                    "(warn/crit at 5 minutes 0 seconds/1 hour 0 minutes)",
                ),
                Metric("last_sync_time", 600.0, levels=(300.0, 3600.0)),
            ],
            id="alert delay WARN",
        ),
        pytest.param(
            4000.0,
            [
                Result(
                    state=State.CRIT,
                    summary="Time since last sync: 1 hour 6 minutes "
                    "(warn/crit at 5 minutes 0 seconds/1 hour 0 minutes)",
                ),
                Metric("last_sync_time", 4000.0, levels=(300.0, 3600.0)),
            ],
            id="alert delay CRIT",
        ),
    ],
)
def test_check_timesyncd_default_alert_delay(
    monkeypatch: pytest.MonkeyPatch,
    seconds_since_last_sync: float,
    sync_result: CheckResult,
) -> None:
    """Without a sync time in the agent output the default alert delay levels apply."""
    server_time = 1569922400.0
    monkeypatch.setattr(
        timesyncd,
        "get_value_store",
        lambda: {"time_server": server_time - seconds_since_last_sync},
    )
    section = timesyncd.parse_timesyncd(
        _string_table(offset="100ms", jitter="0", stratum="2", synced=False)
    )
    with time_machine.travel(
        datetime.datetime.fromtimestamp(server_time, tz=ZoneInfo("UTC")), tick=False
    ):
        assert list(
            timesyncd.check_timesyncd(timesyncd.default_check_parameters, section, None)
        ) == [
            Result(state=State.OK, summary="Offset: 100 milliseconds"),
            Metric("time_offset", 0.1, levels=(0.2, 0.5)),
            *sync_result,
            Result(state=State.OK, summary="Stratum: 2.00"),
            Result(state=State.OK, summary="Jitter: 0 seconds"),
            Metric("jitter", 0.0, levels=(0.2, 0.5)),
            Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
        ]


@pytest.mark.usefixtures("empty_value_store")
@pytest.mark.parametrize(
    "seconds_since_ntp_message, sync_result, ntp_message_result",
    [
        pytest.param(
            60,
            [
                Result(state=State.OK, summary="Time since last sync: 1 minute 0 seconds"),
                Metric("last_sync_time", 60.0),
            ],
            [
                Result(state=State.OK, summary="Time since last NTPMessage: 1 minute 0 seconds"),
                Metric("last_sync_receive_time", 60.36999988555908, levels=(3600.0, 7200.0)),
            ],
            id="last NTP message OK",
        ),
        pytest.param(
            3660,
            [
                Result(state=State.OK, summary="Time since last sync: 1 hour 1 minute"),
                Metric("last_sync_time", 3660.0),
            ],
            [
                Result(
                    state=State.WARN,
                    summary="Time since last NTPMessage: 1 hour 1 minute "
                    "(warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
                ),
                Metric("last_sync_receive_time", 3660.369999885559, levels=(3600.0, 7200.0)),
            ],
            id="last NTP message WARN",
        ),
        pytest.param(
            7260,
            [
                Result(state=State.OK, summary="Time since last sync: 2 hours 1 minute"),
                Metric("last_sync_time", 7260.0),
            ],
            [
                Result(
                    state=State.CRIT,
                    summary="Time since last NTPMessage: 2 hours 1 minute "
                    "(warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
                ),
                Metric("last_sync_receive_time", 7260.369999885559, levels=(3600.0, 7200.0)),
            ],
            id="last NTP message CRIT",
        ),
    ],
)
def test_check_timesyncd_default_last_ntp_message(
    seconds_since_ntp_message: int,
    sync_result: CheckResult,
    ntp_message_result: CheckResult,
) -> None:
    """The default levels on the age of the last NTP message yield OK, WARN and CRIT results."""
    # The NTPMessage was received at 2019-10-01 11:33:12 CEST (= 1569922392.0).
    server_time = 1569922392.37 + seconds_since_ntp_message
    section = timesyncd.parse_timesyncd(_string_table(offset="100ms", jitter="0", stratum="2"))
    section_ntpmessage = timesyncd.parse_timesyncd_ntpmessage(STRING_TABLE_SERVER_NTP_MESSAGE)
    with time_machine.travel(
        datetime.datetime.fromtimestamp(server_time, tz=ZoneInfo("UTC")), tick=False
    ):
        assert list(
            timesyncd.check_timesyncd(
                timesyncd.default_check_parameters, section, section_ntpmessage
            )
        ) == [
            Result(state=State.OK, summary="Offset: 100 milliseconds"),
            Metric("time_offset", 0.1, levels=(0.2, 0.5)),
            *sync_result,
            *ntp_message_result,
            Result(state=State.OK, summary="Stratum: 2.00"),
            Result(state=State.OK, summary="Jitter: 0 seconds"),
            Metric("jitter", 0.0, levels=(0.2, 0.5)),
            Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
        ]


@pytest.mark.parametrize(
    ("ntp_message", "timezone", "expected_timestamp"),
    [
        pytest.param(
            "NTPMessage={ Leap=0, Version=4, Mode=4, Stratum=2, Precision=-23, RootDelay=22.003ms, RootDispersion=21.194ms, Reference=C102015C, OriginateTimestamp=Fri 2019-07-19 13:59:53 IST, ReceiveTimestamp=Fri 2019-07-19 13:59:53 IST, TransmitTimestamp=Fri 2019-07-19 13:59:53 IST, DestinationTimestamp=Fri 2019-07-19 13:59:53 IST, Ignored=no PacketCount=1, Jitter=0 }",
            "Timezone=Europe/Dublin",
            1563541193.0,
            id="ambiguous timezone abbreviation",
        ),
        pytest.param(
            "NTPMessage={ Leap=0, Version=4, Mode=4, Stratum=2, Precision=-23, RootDelay=22.003ms, RootDispersion=21.194ms, Reference=C102015C, OriginateTimestamp=Tue 2023-08-29 21:49:01 AWCST, ReceiveTimestamp=Tue 2023-08-29 21:49:01 AWCST, TransmitTimestamp=Tue 2023-08-29 21:49:01 AWCST, DestinationTimestamp=Tue 2023-08-29 21:49:01 AWCST, Ignored=no PacketCount=1, Jitter=0 }",
            "Timezone=Australia/Eucla",
            1693314241.0,
            id="uncommon timezone abbreviation",
        ),
    ],
)
def test_parse_ntp_message_timestamp(
    ntp_message: str, timezone: str, expected_timestamp: float
) -> None:
    assert timesyncd._parse_ntp_message_timestamp(ntp_message, timezone) == expected_timestamp
