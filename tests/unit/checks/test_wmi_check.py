#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import StringTable

from .checktestlib import Check

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
    "check_name,info",
    [
        ("wmi_webservices", info_wmi_timeout),
        ("dotnet_clrmemory", [["WMItimeout"]]),
    ],
)
def test_wmi_cpu_load_no_discovery(check_name: str, info: StringTable) -> None:
    check = Check(check_name)
    assert not list(check.run_discovery(check.run_parse(info)))
