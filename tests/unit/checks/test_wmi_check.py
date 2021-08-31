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

info_wmi_timeout = [[u'WMItimeout']]

info_msx_info_store_1 = [
    [
        u'AdministrativeRPCrequestsPersec', u'AdminRPCRequests', u'Caption', u'Description',
        u'DirectoryAccessLDAPSearchesPersec', u'Frequency_Object', u'Frequency_PerfTime',
        u'Frequency_Sys100NS', u'JetLogRecordBytesPersec', u'JetLogRecordsPersec',
        u'JetPagesModifiedPersec', u'JetPagesPrereadPersec', u'JetPagesReadPersec',
        u'JetPagesReferencedPersec', u'JetPagesRemodifiedPersec', u'LazyindexescreatedPersec',
        u'LazyindexesdeletedPersec', u'LazyindexfullrefreshPersec',
        u'LazyindexincrementalrefreshPersec', u'MessagescreatedPersec', u'MessagesdeletedPersec',
        u'MessagesopenedPersec', u'MessagesupdatedPersec', u'Name', u'PropertypromotionsPersec',
        u'RPCAverageLatency', u'RPCAverageLatency_Base', u'RPCBytesReceivedPersec',
        u'RPCBytesSentPersec', u'RPCOperationsPersec', u'RPCPacketsPersec', u'RPCRequests',
        u'Timestamp_Object', u'Timestamp_PerfTime', u'Timestamp_Sys100NS'
    ],
    [
        u'13203303', u'0', u'', u'', u'61388', u'0', u'1953125', u'10000000', u'614653228',
        u'12092743', u'49049', u'826', u'312', u'53440863', u'8506178', u'3', u'24', u'3', u'838',
        u'80486', u'23006', u'101226', u'23140', u'_total', u'0', u'1903888', u'3908424', u'1040',
        u'400087174', u'6138327', u'3908424', u'1145789', u'0', u'6743176285319',
        u'130951777565340000'
    ],
]

#.


@pytest.mark.parametrize("check_name,info,expected", [
    ('wmi_webservices', info_wmi_timeout, []),
    ('dotnet_clrmemory', [[u'WMItimeout']], []),
])
def test_wmi_cpu_load_discovery(check_name, info, expected):
    check = Check(check_name)
    discovery_result = DiscoveryResult(check.run_discovery(check.run_parse(info)))
    discovery_expected = DiscoveryResult(expected)
    assertDiscoveryResultsEqual(check, discovery_result, discovery_expected)


@pytest.mark.parametrize("check_name,info,expected", [
    ('wmi_webservices', info_wmi_timeout, None),
])
def test_wmi_timeout_exceptions(check_name, info, expected):
    check = Check(check_name)
    with pytest.raises(MKCounterWrapped):
        CheckResult(check.run_check(None, {}, check.run_parse(info)))


@pytest.mark.parametrize("check_name, expected", [
    ('msexch_isclienttype', [
        (0, 'Average latency: 0.49 ms', [('average_latency', 0.48712422193702626, 40.0, 50.0)]),
        (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60.0, 70.0)]),
    ]),
    ('msexch_isstore', [
        (0, 'Average latency: 0.49 ms', [('average_latency', 0.48712422193702626, 41.0, 51.0)]),
    ]),
])
def test_wmi_msexch_isclienttype_wato_params(check_name, expected):
    check = Check(check_name)
    result = list(
        check.run_check(
            item="_total",
            params={
                'store_latency': (41.0, 51.0),
                'clienttype_latency': (40.0, 50.0),
                'clienttype_requests': (60, 70),
            },
            info=check.run_parse(info_msx_info_store_1),
        ))
    assert result == expected
