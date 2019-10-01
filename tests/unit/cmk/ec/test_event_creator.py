import logging
import time
import pytest
import cmk.ec.defaults
import cmk.ec.main as main


@pytest.fixture
def event_creator():
    logger = logging.getLogger("cmk.mkeventd")

    config = cmk.ec.defaults.default_config()
    config["debug_rules"] = True

    return main.EventCreator(logger, config)


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
                'pid': '8046',
                'core_host': '',
                'host_in_downtime': False,
                'application': 'CRON',
                'host': 'Klapprechner',
                'time': 1558874701.0,
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
                'pid': '8046',
                'priority': 6,
                'text': 'message',
                'time': 1558874701.0
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
            "<154>@1341847712;5;Contact Info;  MyHost My Service: CRIT - This che",
            {
                # TODO: Found a bug? This is not parsed corectly. Check whether or not mkevent
                # really sends these messages
                'application': ' MyHost My Service',
                'core_host': '',
                'facility': 19,
                'host': 'Info;',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'pid': 0,
                'priority': 2,
                'sl': 5,
                'text': 'CRIT - This che',
                'time': 1341847712.0
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
                'time': 1341847712.0
            },
        ),
        (
            # Variant 5: syslog message
            #  Timestamp is RFC3339 with additional restrictions:
            #  - The "T" and "Z" characters in this syntax MUST be upper case.
            #  - Usage of the "T" character is REQUIRED.
            #  - Leap seconds MUST NOT be used.
            "<166>2013-04-05T13:49:31.685Z esx Vpxa: message....",
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
                'time': 1365162571.0
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
                'pid': '7122',
                'priority': 4,
                'text': 'listening for IKE messages',
                'time': 1427281326.0
            },
        ),
        (
            # Variant 9: syslog message (RFC 5424)
            "<134>1 2016-06-02T12:49:05.181+02:00 chrissw7 ChrisApp - TestID - coming from  java code",
            {
                'application': 'ChrisApp',
                'core_host': '',
                'facility': 16,
                'host': 'chrissw7',
                'host_in_downtime': False,
                'ipaddress': '127.0.0.1',
                'priority': 6,
                'text': 'coming from  java code',
                'time': 1464864545.0
            },
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
                'time': 1464270107.0
            },
        ),
    ])
def test_create_event_from_line(event_creator, monkeypatch, line, expected):
    monkeypatch.setattr(
        time,
        'time',
        lambda: 1550000000.0,
    )
    monkeypatch.setattr(
        time,
        'localtime',
        lambda: time.struct_time((2019, 2, 12, 20, 33, 20, 1, 43, 0)),
    )

    address = ("127.0.0.1", 1234)
    assert event_creator.create_event_from_line(line, address) == expected
