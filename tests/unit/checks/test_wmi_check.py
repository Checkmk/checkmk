#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from cmk.base.check_api import MKCounterWrapped

from .checktestlib import assertDiscoveryResultsEqual, CheckResult, DiscoveryResult

pytestmark = pytest.mark.checks

#   .--infos---------------------------------------------------------------.
#   |                        _        __                                   |
#   |                       (_)_ __  / _| ___  ___                         |
#   |                       | | '_ \| |_ / _ \/ __|                        |
#   |                       | | | | |  _| (_) \__ \                        |
#   |                       |_|_| |_|_|  \___/|___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

info_wmi_timeout = [["WMItimeout"]]

info_msx_info_store_1 = [
    [
        "AdministrativeRPCrequestsPersec",
        "AdminRPCRequests",
        "Caption",
        "Description",
        "DirectoryAccessLDAPSearchesPersec",
        "Frequency_Object",
        "Frequency_PerfTime",
        "Frequency_Sys100NS",
        "JetLogRecordBytesPersec",
        "JetLogRecordsPersec",
        "JetPagesModifiedPersec",
        "JetPagesPrereadPersec",
        "JetPagesReadPersec",
        "JetPagesReferencedPersec",
        "JetPagesRemodifiedPersec",
        "LazyindexescreatedPersec",
        "LazyindexesdeletedPersec",
        "LazyindexfullrefreshPersec",
        "LazyindexincrementalrefreshPersec",
        "MessagescreatedPersec",
        "MessagesdeletedPersec",
        "MessagesopenedPersec",
        "MessagesupdatedPersec",
        "Name",
        "PropertypromotionsPersec",
        "RPCAverageLatency",
        "RPCAverageLatency_Base",
        "RPCBytesReceivedPersec",
        "RPCBytesSentPersec",
        "RPCOperationsPersec",
        "RPCPacketsPersec",
        "RPCRequests",
        "Timestamp_Object",
        "Timestamp_PerfTime",
        "Timestamp_Sys100NS",
    ],
    [
        "13203303",
        "0",
        "",
        "",
        "61388",
        "0",
        "1953125",
        "10000000",
        "614653228",
        "12092743",
        "49049",
        "826",
        "312",
        "53440863",
        "8506178",
        "3",
        "24",
        "3",
        "838",
        "80486",
        "23006",
        "101226",
        "23140",
        "_total",
        "0",
        "1903888",
        "3908424",
        "1040",
        "400087174",
        "6138327",
        "3908424",
        "1145789",
        "0",
        "6743176285319",
        "130951777565340000",
    ],
]

# .


@pytest.mark.parametrize(
    "check_name,info,expected",
    [
        ("wmi_webservices", info_wmi_timeout, []),
        ("dotnet_clrmemory", [["WMItimeout"]], []),
    ],
)
def test_wmi_cpu_load_discovery(check_name, info, expected) -> None:
    check = Check(check_name)
    discovery_result = DiscoveryResult(check.run_discovery(check.run_parse(info)))
    discovery_expected = DiscoveryResult(expected)
    assertDiscoveryResultsEqual(check, discovery_result, discovery_expected)


@pytest.mark.parametrize(
    "check_name,info,expected",
    [
        ("wmi_webservices", info_wmi_timeout, None),
    ],
)
def test_wmi_timeout_exceptions(check_name, info, expected) -> None:
    check = Check(check_name)
    with pytest.raises(MKCounterWrapped):
        CheckResult(check.run_check(None, {}, check.run_parse(info)))


@pytest.mark.parametrize(
    "check_name, expected",
    [
        (
            "msexch_isclienttype",
            [
                (
                    0,
                    "Average latency: 0.49 ms",
                    [("average_latency", 0.48712422193702626, 40.0, 50.0)],
                ),
                (0, "RPC Requests/sec: 0.00", [("requests_per_sec", 0.0, 60.0, 70.0)]),
            ],
        ),
        (
            "msexch_isstore",
            [
                (
                    0,
                    "Average latency: 0.49 ms",
                    [("average_latency", 0.48712422193702626, 41.0, 51.0)],
                ),
            ],
        ),
    ],
)
def test_wmi_msexch_isclienttype_wato_params(check_name, expected) -> None:
    check = Check(check_name)
    result = list(
        check.run_check(
            item="_total",
            params={
                "store_latency": (41.0, 51.0),
                "clienttype_latency": (40.0, 50.0),
                "clienttype_requests": (60, 70),
            },
            info=check.run_parse(info_msx_info_store_1),
        )
    )
    assert result == expected
