#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'msexch_rpcclientaccess'

info = [
    [
        u'ActiveUserCount', u'Caption', u'ClientBackgroundRPCsFailed',
        u'ClientBackgroundRPCssucceeded', u'ClientForegroundRPCsFailed',
        u'ClientForegroundRPCssucceeded', u'ClientLatency10secRPCs', u'ClientLatency2secRPCs',
        u'ClientLatency5secRPCs', u'ClientRPCsattempted', u'ClientRPCsFailed',
        u'ClientRPCssucceeded', u'ConnectionCount', u'Description', u'Frequency_Object',
        u'Frequency_PerfTime', u'Frequency_Sys100NS', u'Name', u'RPCAveragedLatency',
        u'RPCClientsBytesRead', u'RPCClientsBytesWritten', u'RPCClientsUncompressedBytesRead',
        u'RPCClientsUncompressedBytesWritten', u'RPCdispatchtaskactivethreads',
        u'RPCdispatchtaskoperationsPersec', u'RPCdispatchtaskqueuelength',
        u'RPCdispatchtaskthreads', u'RpcHttpConnectionRegistrationdispatchtaskactivethreads',
        u'RpcHttpConnectionRegistrationdispatchtaskoperationsPersec',
        u'RpcHttpConnectionRegistrationdispatchtaskqueuelength',
        u'RpcHttpConnectionRegistrationdispatchtaskthreads', u'RPCOperationsPersec',
        u'RPCPacketsPersec', u'RPCRequests', u'Timestamp_Object', u'Timestamp_PerfTime',
        u'Timestamp_Sys100NS', u'UserCount', u'XTCdispatchtaskactivethreads',
        u'XTCdispatchtaskoperationsPersec', u'XTCdispatchtaskqueuelength', u'XTCdispatchtaskthreads'
    ],
    [
        u'11', u'', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'', u'0',
        u'2343747', u'10000000', u'', u'18', u'5368614', u'26082981', u'5368614', u'26082981', u'0',
        u'79928', u'0', u'40', u'0', u'125960', u'0', u'32', u'24218', u'72654', u'0', u'0',
        u'1025586759765', u'131287884133440000', u'0', u'0', u'0', u'0', u'0'
    ],
]

discovery = {'': [(None, None)]}

checks = {
    '': [
        (None, {'latency': (200.0, 250.0), 'requests': (30, 40)}, [
            (0, 'Average latency: 18 ms', [
                ('average_latency', 18.0, 200.0, 250.0, None, None),
            ]),
            (0, 'RPC Requests/sec: 0.00', [
                ('requests_per_sec', 0.0, 30, 40, None, None),
            ]),
            (0, 'Users: 0', [
                ('current_users', 0.0, None, None, None, None),
            ]),
            (0, 'Active users: 11', [
                ('active_users', 11.0, None, None, None, None),
            ]),
        ]),
    ],
}
