#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import logging
from collections.abc import Mapping
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.ccc.hostaddress import HostName

from cmk.ec.event import (
    _split_syslog_nonnil_sd_and_message,
    create_event_from_syslog_message,
    Event,
    parse_iso_8601_timestamp,
    parse_rfc5424_syslog_info,
    parse_syslog_info,
    parse_syslog_message_structured_data,
    remove_leading_bom,
    split_syslog_structured_data_and_message,
)


@pytest.mark.parametrize(
    "data,expected",
    [
        (
            # Variant 1: plain syslog message without priority/facility
            b"May 26 13:45:01 Klapprechner CRON[8046]:  message",
            {
                "priority": 5,
                "facility": 1,
                "text": "message",
                "pid": 8046,
                "core_host": None,
                "host_in_downtime": False,
                "application": "CRON",
                "host": "Klapprechner",
                "time": 1558871101.0,
                "ipaddress": "127.0.0.1",
            },
        ),
        (
            b"Feb 13 08:41:07 pfsp: The configuration was changed on leader blatldc1-xxx to version 1.1366 by blatldc1-xxx/admin at 2019-02-13 09:41:02 CET",
            {
                "application": "pfsp",
                "core_host": None,
                "facility": 1,
                "host": "127.0.0.1",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "pid": 0,
                "priority": 5,
                "text": "The configuration was changed on leader blatldc1-xxx to version 1.1366 by blatldc1-xxx/admin at 2019-02-13 09:41:02 CET",
                "time": 1550043667.0,
            },
        ),
        (
            # Variant 2: syslog message including facility (RFC 3164)
            b"<78>May 26 13:45:01 Klapprechner CRON[8046]:  message",
            {
                "application": "CRON",
                "core_host": None,
                "facility": 9,
                "host": "Klapprechner",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "pid": 8046,
                "priority": 6,
                "text": "message",
                "time": 1558871101.0,
            },
        ),
        (
            # Variant 2: zypper SLES15 without forwarding(?)
            b"<10>Aug 31 14:34:18 localhost RPM[1386]: foo bar baz",
            {
                "application": "RPM",
                "core_host": None,
                "facility": 1,
                "host": "localhost",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "priority": 2,
                "text": "foo bar baz",
                "time": 1535718858.0,
                "pid": 1386,
            },
        ),
        (
            # Variant 2a: zypper SLES15
            b"<10>Aug 31 14:34:18 localhost [RPM][1386]: foo bar baz",
            {
                "application": "RPM",
                "core_host": None,
                "facility": 1,
                "host": "localhost",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "priority": 2,
                "text": "foo bar baz",
                "time": 1535718858.0,
                "pid": 1386,
            },
        ),
        (
            b"<134>Jan 24 10:04:57 xygtldc-blaaa-pn02 pfsp: The configuration was changed on leader xygtldc-blaaa-pn02 to version 1111111 by xygtldc-blaaa-pn02/admin at 2019-01-18 11:04:54 CET",
            {
                "application": "pfsp",
                "core_host": None,
                "facility": 16,
                "host": "xygtldc-blaaa-pn02",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "pid": 0,
                "priority": 6,
                "text": "The configuration was changed on leader xygtldc-blaaa-pn02 to version 1111111 by xygtldc-blaaa-pn02/admin at 2019-01-18 11:04:54 CET",
                "time": 1548320697.0,
            },
        ),
        (
            # Variant 3: local Nagios alert posted by mkevent -n
            b"<154>@1341847712;5;Contact Info; MyHost My Service: CRIT - This che",
            {
                "application": "My Service",
                "contact": "Contact Info",
                "core_host": None,
                "facility": 19,
                "host": "MyHost",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "priority": 2,
                "sl": 5,
                "text": "CRIT - This che",
                "time": 1341847712.0,
                "pid": 0,
            },
        ),
        (
            # Variant 4: remote Nagios alert posted by mkevent -n -> syslog
            b"<154>Jul  9 17:28:32 Klapprechner @1341847712;5;Contact Info;  MyHost My Service: CRIT - This che",
            {
                "application": "My Service",
                "contact": "Contact Info",
                "core_host": None,
                "facility": 19,
                "host": "MyHost",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "priority": 2,
                "sl": 5,
                "text": "CRIT - This che",
                "time": 1341847712.0,
                "pid": 0,
            },
        ),
        (
            # Variant 5: syslog message (RFC3339), subseconds + Zulu time
            b"<166>2013-04-05T13:49:31.625Z esx Vpxa: message....",
            {
                "application": "Vpxa",
                "core_host": None,
                "facility": 20,
                "host": "esx",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "pid": 0,
                "priority": 6,
                "text": "message....",
                "time": 1365169771.625,
            },
        ),
        (
            # Variant 5: syslog message (RFC3339), timezone offset
            b"<166>2013-04-05T13:49:31+02:00 esx Vpxa: message....",
            {
                "application": "Vpxa",
                "core_host": None,
                "facility": 20,
                "host": "esx",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "pid": 0,
                "priority": 6,
                "text": "message....",
                "time": 1365162571,
            },
        ),
        (
            pytest.param(
                b"<133>2023-09-29 18:41:55 host 51890 message....",
                Event(
                    application="",
                    core_host=None,
                    facility=16,
                    host=HostName("host"),
                    host_in_downtime=False,
                    ipaddress="127.0.0.1",
                    pid=51890,
                    priority=5,
                    text="message....",
                    time=1696005715.0,
                ),
                id="Variant 11: TP-Link T1500G-8T 2.0",
            )
        ),
        (
            # Variant 6: syslog message without date / host:
            b"<5>SYSTEM_INFO: [WLAN-1] Triggering Background Scan",
            {
                "application": "SYSTEM_INFO",
                "core_host": None,
                "facility": 0,
                "host": "127.0.0.1",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "pid": 0,
                "priority": 5,
                "text": "[WLAN-1] Triggering Background Scan",
                "time": 1550000000.0,
            },
        ),
        (
            # Variant 7: logwatch.ec event forwarding
            b"<78>@1341847712 Klapprechner /var/log/syslog: message....",
            {
                "application": "/var/log/syslog",
                "core_host": None,
                "facility": 9,
                "host": "Klapprechner",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "pid": 0,
                "priority": 6,
                "text": "message....",
                "time": 1341847712.0,
            },
        ),
        (
            # Variant 7a: Event simulation
            b"<78>@1341847712;3 Klapprechner /var/log/syslog: bzong",
            {
                "application": "/var/log/syslog",
                "core_host": None,
                "facility": 9,
                "host": "Klapprechner",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "pid": 0,
                "priority": 6,
                "sl": 3,
                "text": "bzong",
                "time": 1341847712.0,
            },
        ),
        (
            # Variant 8: syslog message from sophos firewall
            b"<84>2015:03:25-12:02:06 gw pluto[7122]: listening for IKE messages",
            {
                "application": "pluto",
                "core_host": None,
                "facility": 10,
                "host": "gw",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "pid": 7122,
                "priority": 4,
                "text": "listening for IKE messages",
                "time": 1427281326.0,
            },
        ),
        pytest.param(
            b"<134>1 2016-06-02T12:49:05.125Z chrissw7 ChrisApp - TestID - coming from  java code",
            {
                "application": "ChrisApp",
                "core_host": None,
                "facility": 16,
                "host": "chrissw7",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "priority": 6,
                "text": "coming from  java code",
                "time": 1464871745.125,
                "pid": 0,
            },
            id="variant 9: syslog message (RFC 5424)",
        ),
        pytest.param(
            "<134>1 2016-06-02T12:49:05+02:00 chrissw7 ChrisApp - TestID - \ufeffcoming from  java code".encode(),
            {
                "application": "ChrisApp",
                "core_host": None,
                "facility": 16,
                "host": "chrissw7",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "priority": 6,
                "text": "coming from  java code",
                "time": 1464864545,
                "pid": 0,
            },
            id="variant 9: syslog message (RFC 5424) with BOM",
        ),
        pytest.param(
            '<134>1 2016-06-02T12:49:05.125+02:00 chrissw7 ChrisApp - TestID [exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"] \ufeffcoming \ufefffrom  java code'.encode(),
            {
                "application": "ChrisApp",
                "core_host": None,
                "facility": 16,
                "host": "chrissw7",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "priority": 6,
                "text": '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"] coming \ufefffrom  java code',
                "time": 1464864545.125,
                "pid": 0,
            },
            id="variant 9: syslog message (RFC 5424) with structured data",
        ),
        pytest.param(
            rb'<134>1 2016-06-02T12:49:05-01:30 chrissw7 ChrisApp - TestID [exampleSDID@32473 iut="3" eventSource="Appli\] cation" eventID="1\"011"][xyz@123 a="b"] coming from  java code',
            {
                "application": "ChrisApp",
                "core_host": None,
                "facility": 16,
                "host": "chrissw7",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "priority": 6,
                "text": r'[exampleSDID@32473 iut="3" eventSource="Appli\] cation" eventID="1\"011"][xyz@123 a="b"] coming from  java code',
                "time": 1464877145,
                "pid": 0,
            },
            id="variant 9: syslog message (RFC 5424) with mean structured data, no override",
        ),
        pytest.param(
            r'<134>1 2016-06-02T12:49:05.5+02:00 chrissw7 ChrisApp - TestID [Checkmk@18662 sl="0" ipaddress="1.2.3.4" host="host with spaces" application="weird Ƈ ƒ"][exampleSDID@32473 iut="3" eventSource="\"App[lication" eventID="1011\]"] coming from  java code'.encode(),
            {
                "application": "weird Ƈ ƒ",
                "core_host": None,
                "facility": 16,
                "host": "host with spaces",
                "host_in_downtime": False,
                "ipaddress": "1.2.3.4",
                "priority": 6,
                "text": r'[exampleSDID@32473 iut="3" eventSource="\"App[lication" eventID="1011\]"] coming from  java code',
                "time": 1464864545.5,
                "pid": 0,
                "sl": 0,
            },
            id="variant 9: syslog message (RFC 5424) with structured data and override",
        ),
        pytest.param(
            b"<134>1 2021-06-02T13:54:35+00:00 heute /var/log/syslog - - [Checkmk@18662] Jun 2 15:54:24 klappjohe systemd[540514]: Stopped target Main User Target.",
            {
                "application": "/var/log/syslog",
                "core_host": None,
                "facility": 16,
                "host": "heute",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "pid": 0,
                "priority": 6,
                "text": "Jun 2 15:54:24 klappjohe systemd[540514]: Stopped target Main User Target.",
                "time": 1622642075.0,
            },
            id="variant 9: syslog message (RFC 5424) from logwatch forwarding",
        ),
        pytest.param(
            rb'<138>1 2022-11-22T12:36:46+00:00 sup-12385 - - - [Checkmk@18662 application="c:\\Users\\SA-Prd-RPAAdmin5\\AppData\\Local\\UiPath\\Logs\\2022-11-21_Execution.log"] error 16',
            {
                "application": "c:\\Users\\SA-Prd-RPAAdmin5\\AppData\\Local\\UiPath\\Logs\\2022-11-21_Execution.log",
                "core_host": None,
                "facility": 17,
                "host": "sup-12385",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "pid": 0,
                "priority": 2,
                "text": "error 16",
                "time": 1669120606.0,
            },
            id="variant 9: syslog message (RFC 5424) from Windows logwatch forwarding",
        ),
        (
            # Variant 10:
            b"2016 May 26 15:41:47 IST XYZ Ebra: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet45 (XXX.ASAD.Et45), changed state to up year month day hh:mm:ss timezone HOSTNAME KeyAgent:",
            {
                "application": "Ebra",
                "core_host": None,
                "facility": 1,
                "host": "XYZ",
                "host_in_downtime": False,
                "ipaddress": "127.0.0.1",
                "priority": 5,
                "text": "%LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet45 (XXX.ASAD.Et45), changed state to up year month day hh:mm:ss timezone HOSTNAME KeyAgent:",
                "time": 1464270107.0,
                "pid": 0,
            },
        ),
    ],
)
def test_create_event_from_syslog_message(data: bytes, expected: Mapping[str, object]) -> None:
    address = ("127.0.0.1", 1234)
    logger = logging.getLogger("cmk.mkeventd")

    with time_machine.travel(
        datetime.datetime.fromtimestamp(1550000000, tz=ZoneInfo("CET")), tick=False
    ):
        assert create_event_from_syslog_message(data, address, logger) == expected


@pytest.mark.parametrize(
    "data, expected",
    [
        pytest.param(
            b"May 26 13:45:01 Klapprechner CRON[8046]:  message",
            {
                "priority": 5,
                "facility": 1,
                "text": "message",
                "pid": 8046,
                "core_host": None,
                "host_in_downtime": False,
                "application": "CRON",
                "host": "Klapprechner",
                "time": 1685101501.0,  # Fri May 26 2023 13:45:01 GMT+0200
                "ipaddress": "127.0.0.1",
            },
        ),
    ],
)
def test_create_event_from_syslog_message_with_DST(
    data: bytes, expected: Mapping[str, object]
) -> None:
    address = ("127.0.0.1", 1234)
    logger = logging.getLogger("cmk.mkeventd")

    with time_machine.travel(
        datetime.datetime.fromtimestamp(1675748161, tz=ZoneInfo("CET"))
    ):  # february when there is no DST
        assert create_event_from_syslog_message(data, address, logger) == expected

    with time_machine.travel(
        datetime.datetime.fromtimestamp(1688704561, tz=ZoneInfo("CET"))
    ):  # July when there is DST
        assert create_event_from_syslog_message(data, address, logger) == expected


@pytest.mark.parametrize(
    "data, expected",
    [
        pytest.param(
            b"Feb 08 13:15:01 Klapprechner CRON[8046]:  message",
            {
                "priority": 5,
                "facility": 1,
                "text": "message",
                "pid": 8046,
                "core_host": None,
                "host_in_downtime": False,
                "application": "CRON",
                "host": "Klapprechner",
                "time": 1675858501.0,  # Wed Feb 08 2023 13:15:13 GMT+0100
                "ipaddress": "127.0.0.1",
            },
        ),
    ],
)
def test_create_event_from_syslog_message_without_DST(
    data: bytes, expected: Mapping[str, object]
) -> None:
    address = ("127.0.0.1", 1234)
    logger = logging.getLogger("cmk.mkeventd")

    with time_machine.travel(
        datetime.datetime.fromtimestamp(1675748161, tz=ZoneInfo("CET")), tick=False
    ):  # february when there is no DST
        assert create_event_from_syslog_message(data, address, logger) == expected

    with time_machine.travel(
        datetime.datetime.fromtimestamp(1688704561, tz=ZoneInfo("CET")), tick=False
    ):  # July when there is DST
        assert create_event_from_syslog_message(data, address, logger) == expected


@pytest.mark.parametrize(
    "line, expected_result",
    [
        pytest.param(
            "App42Blah[4711]: a message",
            {
                "application": "App42Blah",
                "pid": 4711,
                "text": "a message",
            },
            id="content with both application and pid",
        ),
        pytest.param(
            "App42Blah[-]: a message",
            {
                "application": "App42Blah",
                "pid": 0,
                "text": "a message",
            },
            id="content with application and an undefined pid",
        ),
        pytest.param(
            "App42Blah: a message",
            {
                "application": "App42Blah",
                "pid": 0,
                "text": "a message",
            },
            id="content with application and without pid",
        ),
        pytest.param(
            "App42Blah a message",
            {
                "application": "",
                "pid": 0,
                "text": "App42Blah a message",
            },
            id="content with neither application nor pid",
        ),
        pytest.param(
            "C:/this/is/no/tag a message",
            {
                "application": "",
                "pid": 0,
                "text": "C:/this/is/no/tag a message",
            },
            id="content with Windows path at the beginning",
        ),
    ],
)
def test_parse_syslog_info(line: str, expected_result: Mapping[str, object]) -> None:
    assert parse_syslog_info(line) == expected_result


@pytest.mark.parametrize(
    "line, expected_result",
    [
        pytest.param(
            "1 2021-04-08T06:47:17+00:00 herbert some_deamon - - - something is wrong with herbert",
            {
                "application": "some_deamon",
                "host": "herbert",
                "text": "something is wrong with herbert",
                "time": 1617864437.0,
                "pid": 0,
            },
            id="no structured data",
        ),
        pytest.param(
            '1 2021-04-08T06:47:17+00:00 - - - - [whatever@345 a="b" c="d"][Checkmk@18662 sl="30" ipaddress="3.6.9.0" host="Westfold, Middleearth, 3rd Age of the Ring" application="Legolas Greenleaf"] They\'re taking the Hobbits to Isengard!',
            {
                "application": "Legolas Greenleaf",
                "host": "Westfold, Middleearth, 3rd Age of the Ring",
                "ipaddress": "3.6.9.0",
                "text": '[whatever@345 a="b" c="d"] They\'re taking the Hobbits to Isengard!',
                "time": 1617864437.0,
                "pid": 0,
                "sl": 30,
            },
            id="with structured data and override",
        ),
        pytest.param(
            "1 - herbert some_deamon - - - \ufeffsomething is wrong with herbert",
            {
                "application": "some_deamon",
                "host": "herbert",
                "text": "something is wrong with herbert",
                "time": 1550000000.0,
                "pid": 0,
            },
            id="no timestamp",
        ),
    ],
)
def test_parse_rfc5424_syslog_info(line: str, expected_result: Mapping[str, object]) -> None:
    # this is currently needed because we do not use the timezone information from the log message

    with time_machine.travel(
        datetime.datetime.fromtimestamp(1550000000, tz=ZoneInfo("UTC")), tick=False
    ):
        assert parse_rfc5424_syslog_info(line) == expected_result


@pytest.mark.parametrize(
    "timestamp, expected_result",
    [
        pytest.param(
            "2003-10-11T22:14:15Z",
            1065910455.0,
            id="UTC, no fractional seconds",
        ),
        pytest.param(
            "2003-10-11T22:14:15.25Z",
            1065910455.25,
            id="UTC with fractional seconds",
        ),
        pytest.param(
            "2003-10-11T22:14:15+01:00",
            1065906855.0,
            id="custom timezone, no fractional seconds",
        ),
        pytest.param(
            "2003-10-11T22:14:15.75+01:00",
            1065906855.75,
            id="custom timezone, with fractional seconds",
        ),
    ],
)
def test_parse_syslog_timestamp(timestamp: str, expected_result: float) -> None:
    assert parse_iso_8601_timestamp(timestamp) == expected_result


@pytest.mark.parametrize(
    "teststr, expected_result",
    [
        pytest.param(
            "abc123",
            "abc123",
            id="no bom",
        ),
        pytest.param(
            "\ufeffabc123",
            "abc123",
            id="bom at the beginning",
        ),
        pytest.param(
            "\ufeffabc\ufeff123",
            "abc\ufeff123",
            id="bom at the beginning at in the middle",
        ),
    ],
)
def test_remove_leading_bom(teststr: str, expected_result: str) -> None:
    assert remove_leading_bom(teststr) == expected_result


@pytest.mark.parametrize(
    "sd_and_message, expected_result",
    [
        pytest.param(
            '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"][examplePriority@32473 class="high"] Red alert, shields up!',
            (
                '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"][examplePriority@32473 class="high"]',
                "Red alert, shields up!",
            ),
            id="with structured data",
        ),
        pytest.param(
            "- Red alert, shields up!",
            (
                None,
                "Red alert, shields up!",
            ),
            id="without structured data",
        ),
    ],
)
def test_split_syslog_structured_data_and_message(
    sd_and_message: str, expected_result: tuple[str | None, str]
) -> None:
    assert split_syslog_structured_data_and_message(sd_and_message) == expected_result


@pytest.mark.parametrize(
    "sd_and_message, expected_result",
    [
        pytest.param(
            '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"][examplePriority@32473 class="high"] Red alert, shields up!',
            (
                '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"][examplePriority@32473 class="high"]',
                "Red alert, shields up!",
            ),
            id="normal structured data",
        ),
        pytest.param(
            r'[exampleSDID@32473 iut="3" eventSource="App\"lication" eventID="1011"][exampleP\"\]riority@32473 class="h\] igh"] Red alert, shields up!',
            (
                r'[exampleSDID@32473 iut="3" eventSource="App\"lication" eventID="1011"][exampleP\"\]riority@32473 class="h\] igh"]',
                "Red alert, shields up!",
            ),
            id="mean structured data",
        ),
        pytest.param(
            "[exampleSDID@32473][examplePriority@32473] Red alert, shields up!",
            (
                "[exampleSDID@32473][examplePriority@32473]",
                "Red alert, shields up!",
            ),
            id="structured data without parameters",
        ),
        pytest.param(
            '[exampleSDID@32473 iut="3" eventSource="Application"][examplePriority@32473] Red alert, shields up!',
            (
                '[exampleSDID@32473 iut="3" eventSource="Application"][examplePriority@32473]',
                "Red alert, shields up!",
            ),
            id="structured data with and without parameters mixed 1",
        ),
        pytest.param(
            '[examplePriority@32473][exampleSDID@32473 iut="3" eventSource="Application"] Red alert, shields up!',
            (
                '[examplePriority@32473][exampleSDID@32473 iut="3" eventSource="Application"]',
                "Red alert, shields up!",
            ),
            id="structured data with and without parameters mixed 2",
        ),
        pytest.param(
            '[exampleSDID@32473 iut="3"] funny message which looks like sd: [exampleSDID@32473 iut="3"] abc',
            (
                '[exampleSDID@32473 iut="3"]',
                'funny message which looks like sd: [exampleSDID@32473 iut="3"] abc',
            ),
            id="mean message which contains something which looks like structured data",
        ),
        pytest.param(
            '[exampleSDID@32473 iut="3"][examplePriority@32473 eventSource="Application"]',
            (
                '[exampleSDID@32473 iut="3"][examplePriority@32473 eventSource="Application"]',
                "",
            ),
            id="no message",
        ),
    ],
)
def test_split_syslog_nonnil_sd_and_message(
    sd_and_message: str,
    expected_result: tuple[str, str],
) -> None:
    assert _split_syslog_nonnil_sd_and_message(sd_and_message) == expected_result


@pytest.mark.parametrize(
    "sd_and_message",
    [
        pytest.param(
            '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"][examplePriority@32473 class="high" \ufeffRed alert, shields up!',
            id="missing closing bracket",
        ),
        pytest.param(
            "\ufeffRed alert, shields up!",
            id="no structured data",
        ),
    ],
)
def test_split_syslog_structured_data_and_message_exception(sd_and_message: str) -> None:
    with pytest.raises(
        ValueError, match="Invalid RFC 5424 syslog message: structured data has the wrong format"
    ):
        split_syslog_structured_data_and_message(sd_and_message)


@pytest.mark.parametrize(
    "structured_data, expected_result",
    [
        pytest.param(
            '[Checkmk@18662 sl="0" ipaddress="3.6.9.0" host="Westfold, Middleearth, 3rd Age of the Ring" application="Legolas Greenleaf"]',
            (
                {
                    "sl": "0",
                    "ipaddress": "3.6.9.0",
                    "host": "Westfold, Middleearth, 3rd Age of the Ring",
                    "application": "Legolas Greenleaf",
                },
                "",
            ),
            id="checkmk structured data only",
        ),
        pytest.param(
            '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"][Checkmk@18662 sl="0" ipaddress="127.0.0.1" host="locÄl hést" application="ŕŖŗ"][examplePriority@32473 class="high"]',
            (
                {
                    "sl": "0",
                    "ipaddress": "127.0.0.1",
                    "host": "locÄl hést",
                    "application": "ŕŖŗ",
                },
                '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"][examplePriority@32473 class="high"]',
            ),
            id="checkmk and other structured data",
        ),
        pytest.param(
            '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"][examplePriority@32473 class="high"]',
            (
                {},
                '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"][examplePriority@32473 class="high"]',
            ),
            id="no checkmk structured data",
        ),
        pytest.param(
            r'[Checkmk@18662 sl="10" host="abc\" def" application="[mean\]"]',
            (
                {
                    "sl": "10",
                    "host": 'abc" def',
                    "application": "[mean]",
                },
                "",
            ),
            id="with escaping in checkmk structured data",
        ),
        pytest.param(
            "[Checkmk@18662]",
            (
                {},
                "",
            ),
            id="checkmk structured data without parameters",
        ),
    ],
)
def test_parse_syslog_message_structured_data(
    structured_data: str,
    expected_result: tuple[Mapping[str, str], str],
) -> None:
    assert parse_syslog_message_structured_data(structured_data) == expected_result


def test_parse_syslog_message_structured_data_exception() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid RFC 5424 syslog message: Found Checkmk structured data element multiple times",
    ):
        parse_syslog_message_structured_data(
            '[Checkmk@18662 sl="0" ipaddress="127.0.0.1"][Checkmk@18662 sl="0" ipaddress="127.0.0.2"]'
        )
