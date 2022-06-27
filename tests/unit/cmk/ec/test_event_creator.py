#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name,line-too-long
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

import logging
from typing import Any, Mapping, Optional, Tuple

import pytest

from tests.testlib import on_time

from cmk.ec.event import (
    _split_syslog_nonnil_sd_and_message,
    create_event_from_line,
    parse_iso_8601_timestamp,
    parse_rfc5424_syslog_info,
    parse_syslog_info,
    parse_syslog_message_structured_data,
    remove_leading_bom,
    split_syslog_structured_data_and_message,
)


@pytest.mark.parametrize(
    "line,expected",
    [
        (
            # Variant 1: plain syslog message without priority/facility
            "May 26 13:45:01 Klapprechner CRON[8046]:  message",
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
            "Feb 13 08:41:07 pfsp: The configuration was changed on leader blatldc1-xxx to version 1.1366 by blatldc1-xxx/admin at 2019-02-13 09:41:02 CET",
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
            "<78>May 26 13:45:01 Klapprechner CRON[8046]:  message",
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
            "<134>Jan 24 10:04:57 xygtldc-blaaa-pn02 pfsp: The configuration was changed on leader xygtldc-blaaa-pn02 to version 1111111 by xygtldc-blaaa-pn02/admin at 2019-01-18 11:04:54 CET",
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
            "<154>@1341847712;5;Contact Info; MyHost My Service: CRIT - This che",
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
            "<154>Jul  9 17:28:32 Klapprechner @1341847712;5;Contact Info;  MyHost My Service: CRIT - This che",
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
            "<166>2013-04-05T13:49:31.625Z esx Vpxa: message....",
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
            "<166>2013-04-05T13:49:31+02:00 esx Vpxa: message....",
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
            # Variant 6: syslog message without date / host:
            "<5>SYSTEM_INFO: [WLAN-1] Triggering Background Scan",
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
            "<78>@1341847712 Klapprechner /var/log/syslog: message....",
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
            "<78>@1341847712;3 Klapprechner /var/log/syslog: bzong",
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
            "<84>2015:03:25-12:02:06 gw pluto[7122]: listening for IKE messages",
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
            "<134>1 2016-06-02T12:49:05.125Z chrissw7 ChrisApp - TestID - coming from  java code",
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
            "<134>1 2016-06-02T12:49:05+02:00 chrissw7 ChrisApp - TestID - \ufeffcoming from  java code",
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
            '<134>1 2016-06-02T12:49:05.125+02:00 chrissw7 ChrisApp - TestID [exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"] \ufeffcoming \ufefffrom  java code',
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
            r'<134>1 2016-06-02T12:49:05-01:30 chrissw7 ChrisApp - TestID [exampleSDID@32473 iut="3" eventSource="Appli\] cation" eventID="1\"011"][xyz@123 a="b"] coming from  java code',
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
            r'<134>1 2016-06-02T12:49:05.5+02:00 chrissw7 ChrisApp - TestID [Checkmk@18662 sl="0" ipaddress="1.2.3.4" host="host with spaces" application="weird Ƈ ƒ"][exampleSDID@32473 iut="3" eventSource="\"App[lication" eventID="1011\]"] coming from  java code',
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
            "<134>1 2021-06-02T13:54:35+00:00 heute /var/log/syslog - - [Checkmk@18662] Jun 2 15:54:24 klappjohe systemd[540514]: Stopped target Main User Target.",
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
        (
            # Variant 10:
            "2016 May 26 15:41:47 IST XYZ Ebra: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet45 (XXX.ASAD.Et45), changed state to up year month day hh:mm:ss timezone HOSTNAME KeyAgent:",
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
def test_create_event_from_line(line, expected) -> None:
    address = ("127.0.0.1", 1234)
    logger = logging.getLogger("cmk.mkeventd")
    with on_time(1550000000.0, "CET"):
        assert create_event_from_line(line, address, logger, verbose=True) == expected


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
def test_parse_syslog_info(line: str, expected_result: Mapping[str, Any]) -> None:
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
def test_parse_rfc5424_syslog_info(line: str, expected_result: Mapping[str, Any]) -> None:
    # this is currently needed because we do not use the timezone information from the log message
    with on_time(1550000000.0, "UTC"):
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
    sd_and_message: str, expected_result: Tuple[Optional[str], str]
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
    expected_result: Tuple[str, str],
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
    with pytest.raises(ValueError):
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
            r'[Checkmk@18662 sl="10" host="abc\\" def" application="[mean\]"]',
            (
                {
                    "sl": "10",
                    "host": r'abc\\" def',
                    "application": r"[mean\]",
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
    expected_result: Tuple[Mapping[str, str], str],
) -> None:
    assert parse_syslog_message_structured_data(structured_data) == expected_result


def test_parse_syslog_message_structured_data_exception() -> None:
    with pytest.raises(ValueError):
        parse_syslog_message_structured_data(
            '[Checkmk@18662 sl="0" ipaddress="127.0.0.1"][Checkmk@18662 sl="0" ipaddress="127.0.0.2"]'
        )
