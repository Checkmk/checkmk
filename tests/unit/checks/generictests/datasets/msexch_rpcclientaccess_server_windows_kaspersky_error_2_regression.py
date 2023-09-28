#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "msexch_rpcclientaccess"

mock_item_state = {
    "": {"RPCRequests_": (0, 0)}
}

info = [
    [
        "ActiveUserCount",
        "Caption",
        "ClientBackgroundRPCsFailed",
        "ClientBackgroundRPCssucceeded",
        "ClientForegroundRPCsFailed",
        "ClientForegroundRPCssucceeded",
        "ClientLatency10secRPCs",
        "ClientLatency2secRPCs",
        "ClientLatency5secRPCs",
        "ClientRPCsattempted",
        "ClientRPCsFailed",
        "ClientRPCssucceeded",
        "ConnectionCount",
        "Description",
        "Frequency_Object",
        "Frequency_PerfTime",
        "Frequency_Sys100NS",
        "Name",
        "RPCAveragedLatency",
        "RPCClientsBytesRead",
        "RPCClientsBytesWritten",
        "RPCClientsUncompressedBytesRead",
        "RPCClientsUncompressedBytesWritten",
        "RPCdispatchtaskactivethreads",
        "RPCdispatchtaskoperationsPersec",
        "RPCdispatchtaskqueuelength",
        "RPCdispatchtaskthreads",
        "RpcHttpConnectionRegistrationdispatchtaskactivethreads",
        "RpcHttpConnectionRegistrationdispatchtaskoperationsPersec",
        "RpcHttpConnectionRegistrationdispatchtaskqueuelength",
        "RpcHttpConnectionRegistrationdispatchtaskthreads",
        "RPCOperationsPersec",
        "RPCPacketsPersec",
        "RPCRequests",
        "Timestamp_Object",
        "Timestamp_PerfTime",
        "Timestamp_Sys100NS",
        "UserCount",
        "XTCdispatchtaskactivethreads",
        "XTCdispatchtaskoperationsPersec",
        "XTCdispatchtaskqueuelength",
        "XTCdispatchtaskthreads",
    ],
    [
        "11",
        "",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "",
        "0",
        "2343747",
        "10000000",
        "",
        "18",
        "5368614",
        "26082981",
        "5368614",
        "26082981",
        "0",
        "79928",
        "0",
        "40",
        "0",
        "125960",
        "0",
        "32",
        "24218",
        "72654",
        "0",
        "0",
        "1025586759765",
        "131287884133440000",
        "0",
        "0",
        "0",
        "0",
        "0",
    ],
]

discovery = {"": [(None, None)]}

checks = {
    "": [
        (
            None,
            {"latency": (200.0, 250.0), "requests": (30, 40)},
            [
                (
                    0,
                    "Average latency: 18 ms",
                    [
                        ("average_latency", 18.0, 200.0, 250.0, None, None),
                    ],
                ),
                (
                    0,
                    "RPC Requests/sec: 0.00",
                    [
                        ("requests_per_sec", 0.0, 30, 40, None, None),
                    ],
                ),
                (
                    0,
                    "Users: 0",
                    [
                        ("current_users", 0.0, None, None, None, None),
                    ],
                ),
                (
                    0,
                    "Active users: 11",
                    [
                        ("active_users", 11.0, None, None, None, None),
                    ],
                ),
            ],
        ),
    ],
}
