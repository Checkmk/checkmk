#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.msexch.agent_based.msexch_rpcclientaccess import (
    check_msexch_rpcclientaccess,
    discover_msexch_rpcclientaccess,
    Params,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table

_AGENT_OUTPUT = [
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


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            _AGENT_OUTPUT,
            [
                Service(item=None),
            ],
        ),
    ],
)
def test_parse_msexch_rpcclientaccess(
    string_table: StringTable, expected_result: DiscoveryResult
) -> None:
    section = parse_wmi_table(string_table)
    assert sorted(discover_msexch_rpcclientaccess(section)) == expected_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "string_table, params, expected_result",
    [
        (
            _AGENT_OUTPUT,
            Params(
                latency_s=("fixed", (0.005, 0.01)),
                requests=("no_levels", None),
            ),
            [
                Result(
                    state=State.CRIT,
                    summary="Average latency: 18 milliseconds (warn/crit at 5 milliseconds/10 milliseconds)",
                ),
                Metric("average_latency_s", 0.018, levels=(0.005, 0.01)),
                Result(state=State.OK, summary="RPC Requests/sec: 0.00"),
                Metric("requests_per_sec", 0.0),
                Result(state=State.OK, summary="Users: 0.00"),
                Metric("current_users", 0.0),
                Result(state=State.OK, summary="Active users: 11.00"),
                Metric("active_users", 11.0),
            ],
        ),
    ],
)
def test_check_msexch_rpcclientaccess(
    string_table: StringTable,
    params: Params,
    expected_result: CheckResult,
) -> None:
    get_value_store().update({"RPCRequests_": (0.0, 0.0)})
    section = parse_wmi_table(string_table)
    assert list(check_msexch_rpcclientaccess(params, section)) == expected_result
