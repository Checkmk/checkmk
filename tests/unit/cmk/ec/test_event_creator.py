#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import logging
from typing import Any, Mapping

import pytest

from testlib import on_time, set_timezone

import cmk.ec.export as ec
import cmk.ec.main


@pytest.fixture
def event_creator():
    logger = logging.getLogger("cmk.mkeventd")

    config = ec.default_config()
    config["debug_rules"] = True

    return cmk.ec.main.EventCreator(logger, config)


@pytest.mark.parametrize(
    "line,expected",
    [
        (
            # Variant 1: plain syslog message without priority/facility
            "May 26 13:45:01 Klapprechner CRON[8046]:  message",
            {
                'priority': 5,
                'facility': 1,
                'text': 'message',
                'pid': 8046,
                'core_host': '',
                'host_in_downtime': False,
                'application': 'CRON',
                'host': 'Klapprechner',
                'time': 1558871101.0,
                'ipaddress': '127.0.0.1',
            },
        ),
        (
            "Feb 13 08:41:07 pfsp: The configuration was changed on leader blatldc1-xxx to version 1.1366 by blatldc1-xxx/admin at 2019-02-13 09:41:02 CET",
            {
                'application': 'pfsp',
                'core_host': '',
                'facility': 1,
                'host': '127.0.0.1',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'pid': 0,
                'priority': 5,
                'text': 'The configuration was changed on leader blatldc1-xxx to version 1.1366 by blatldc1-xxx/admin at 2019-02-13 09:41:02 CET',
                'time': 1550043667.0
            },
        ),
        (
            # Variant 2: syslog message including facility (RFC 3164)
            "<78>May 26 13:45:01 Klapprechner CRON[8046]:  message",
            {
                'application': 'CRON',
                'core_host': '',
                'facility': 9,
                'host': 'Klapprechner',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'pid': 8046,
                'priority': 6,
                'text': 'message',
                'time': 1558871101.0
            },
        ),
        (
            "<134>Jan 24 10:04:57 xygtldc-blaaa-pn02 pfsp: The configuration was changed on leader xygtldc-blaaa-pn02 to version 1111111 by xygtldc-blaaa-pn02/admin at 2019-01-18 11:04:54 CET",
            {
                'application': 'pfsp',
                'core_host': '',
                'facility': 16,
                'host': 'xygtldc-blaaa-pn02',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'pid': 0,
                'priority': 6,
                'text': 'The configuration was changed on leader xygtldc-blaaa-pn02 to version 1111111 by xygtldc-blaaa-pn02/admin at 2019-01-18 11:04:54 CET',
                'time': 1548320697.0
            },
        ),
        (
            # Variant 3: local Nagios alert posted by mkevent -n
            "<154>@1341847712;5;Contact Info; MyHost My Service: CRIT - This che",
            {
                'application': 'My Service',
                'contact': 'Contact Info',
                'core_host': '',
                'facility': 19,
                'host': 'MyHost',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'priority': 2,
                'sl': 5,
                'text': 'CRIT - This che',
                'time': 1341847712.0,
                'pid': 0
            },
        ),
        (
            # Variant 4: remote Nagios alert posted by mkevent -n -> syslog
            "<154>Jul  9 17:28:32 Klapprechner @1341847712;5;Contact Info;  MyHost My Service: CRIT - This che",
            {
                'application': 'My Service',
                'contact': 'Contact Info',
                'core_host': '',
                'facility': 19,
                'host': 'MyHost',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'priority': 2,
                'sl': 5,
                'text': 'CRIT - This che',
                'time': 1341847712.0,
                'pid': 0
            },
        ),
        (
            # Variant 5: syslog message (RFC3339), subseconds + Zulu time
            "<166>2013-04-05T13:49:31.625Z esx Vpxa: message....",
            {
                'application': 'Vpxa',
                'core_host': '',
                'facility': 20,
                'host': 'esx',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'pid': 0,
                'priority': 6,
                'text': 'message....',
                'time': 1365169771.625
            },
        ),
        (
            # Variant 5: syslog message (RFC3339), timezone offset
            "<166>2013-04-05T13:49:31+02:00 esx Vpxa: message....",
            {
                'application': 'Vpxa',
                'core_host': '',
                'facility': 20,
                'host': 'esx',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'pid': 0,
                'priority': 6,
                'text': 'message....',
                'time': 1365162571
            },
        ),
        (
            # Variant 6: syslog message without date / host:
            "<5>SYSTEM_INFO: [WLAN-1] Triggering Background Scan",
            {
                'application': 'SYSTEM_INFO',
                'core_host': '',
                'facility': 0,
                'host': '127.0.0.1',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'pid': 0,
                'priority': 5,
                'text': '[WLAN-1] Triggering Background Scan',
                'time': 1550000000.0
            },
        ),
        (
            # Variant 7: logwatch.ec event forwarding
            "<78>@1341847712 Klapprechner /var/log/syslog: message....",
            {
                'application': '/var/log/syslog',
                'core_host': '',
                'facility': 9,
                'host': 'Klapprechner',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'pid': 0,
                'priority': 6,
                'text': 'message....',
                'time': 1341847712.0
            },
        ),
        (
            # Variant 7a: Event simulation
            "<78>@1341847712;3 Klapprechner /var/log/syslog: bzong",
            {
                'application': '/var/log/syslog',
                'core_host': '',
                'facility': 9,
                'host': 'Klapprechner',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'pid': 0,
                'priority': 6,
                'sl': 3,
                'text': 'bzong',
                'time': 1341847712.0
            },
        ),
        (
            # Variant 8: syslog message from sophos firewall
            "<84>2015:03:25-12:02:06 gw pluto[7122]: listening for IKE messages",
            {
                'application': 'pluto',
                'core_host': '',
                'facility': 10,
                'host': 'gw',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'pid': 7122,
                'priority': 4,
                'text': 'listening for IKE messages',
                'time': 1427281326.0
            },
        ),
        pytest.param(
            "<134>1 2016-06-02T12:49:05.125Z chrissw7 ChrisApp - TestID - coming from  java code",
            {
                'application': 'ChrisApp',
                'core_host': '',
                'facility': 16,
                'host': 'chrissw7',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'priority': 6,
                'text': 'coming from  java code',
                'time': 1464871745.125,
                'pid': 0,
            },
            id="variant 9: syslog message (RFC 5424)",
        ),
        pytest.param(
            "<134>1 2016-06-02T12:49:05+02:00 chrissw7 ChrisApp - TestID - \ufeffcoming from  java code",
            {
                'application': 'ChrisApp',
                'core_host': '',
                'facility': 16,
                'host': 'chrissw7',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'priority': 6,
                'text': '\ufeffcoming from  java code',
                'time': 1464864545,
                'pid': 0,
            },
            id="variant 9: syslog message (RFC 5424) with BOM",
        ),
        pytest.param(
            '<134>1 2016-06-02T12:49:05.125+02:00 chrissw7 ChrisApp - TestID [exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"] \ufeffcoming \ufefffrom  java code',
            {
                'application': 'ChrisApp',
                'core_host': '',
                'facility': 16,
                'host': 'chrissw7',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'priority': 6,
                'text': '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"] \ufeffcoming \ufefffrom  java code',
                'time': 1464864545.125,
                'pid': 0,
            },
            id="variant 9: syslog message (RFC 5424) with structured data",
        ),
        pytest.param(
            r'<134>1 2016-06-02T12:49:05-01:30 chrissw7 ChrisApp - TestID [exampleSDID@32473 iut="3" eventSource="Appli\] cation" eventID="1\"011"][xyz@123 a="b"] coming from  java code',
            {
                'application': 'ChrisApp',
                'core_host': '',
                'facility': 16,
                'host': 'chrissw7',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'priority': 6,
                'text': r'[exampleSDID@32473 iut="3" eventSource="Appli\] cation" eventID="1\"011"][xyz@123 a="b"] coming from  java code',
                'time': 1464877145,
                'pid': 0,
            },
            id="variant 9: syslog message (RFC 5424) with mean structured data",
        ),
        (
            # Variant 10:
            "2016 May 26 15:41:47 IST XYZ Ebra: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet45 (XXX.ASAD.Et45), changed state to up year month day hh:mm:ss timezone HOSTNAME KeyAgent:",
            {
                'application': 'Ebra',
                'core_host': '',
                'facility': 1,
                'host': 'XYZ',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'priority': 5,
                'text': '%LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet45 (XXX.ASAD.Et45), changed state to up year month day hh:mm:ss timezone HOSTNAME KeyAgent:',
                'time': 1464270107.0,
                'pid': 0
            },
        ),
    ])
def test_create_event_from_line(event_creator, monkeypatch, line, expected):
    address = ("127.0.0.1", 1234)
    with on_time(1550000000.0, "CET"):
        assert event_creator.create_event_from_line(line, address) == expected


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
def test_parse_syslog_info(event_creator, line: str, expected_result: Mapping[str, Any]) -> None:
    assert event_creator._parse_syslog_info(line) == expected_result


class TestEventCreator:
    @pytest.mark.parametrize(
        "line, expected_result",
        [
            pytest.param(
                "1 2021-04-08T06:47:17+00:00 herbert some_deamon - - - something is wrong with herbert",
                {
                    'application': 'some_deamon',
                    'host': 'herbert',
                    'text': 'something is wrong with herbert',
                    'time': 1617864437.0,
                    'pid': 0,
                },
                id="no structured data",
            ),
            pytest.param(
                '1 2021-04-08T06:47:17+00:00 - - - - [whatever@345 a="b" c="d"][Checkmk@18662 ipaddress="3.6.9.0" host="Westfold, Middleearth, 3rd Age of the Ring" application="Legolas Greenleaf"] They\'re taking the Hobbits to Isengard!',
                {
                    'application': '',
                    'host': '',
                    'text': '[whatever@345 a="b" c="d"][Checkmk@18662 ipaddress="3.6.9.0" host="Westfold, Middleearth, 3rd Age of the Ring" application="Legolas Greenleaf"] They\'re taking the Hobbits to Isengard!',
                    'time': 1617864437.0,
                    'pid': 0,
                },
                id="with structured data",
            ),
        ],
    )
    def test_parse_rfc5424_syslog_info(
        self,
        event_creator: cmk.ec.main.EventCreator,
        line: str,
        expected_result: Mapping[str, Any],
    ) -> None:
        # this is currently needed because we do not use the timezone information from the log message
        with set_timezone("UTC"):
            assert event_creator._parse_rfc5424_syslog_info(line) == expected_result
