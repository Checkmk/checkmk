#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.storeonce.agent_based.storeonce4x_d2d_services import (
    check_storeonce4x_d2d_services,
    discover_storeonce4x_d2d_services,
    parse_storeonce4x_d2d_services,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    '{"services": {"OverallHealth": {"subsystemDescription": "D2D Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "evt-mgr": {"subsystemDescription": "D2D Event Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas-share": {"subsystemDescription": "NAS Share Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "rep-obj-rpc": {"subsystemDescription": "RepObj RPC Server (FME)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "rep-rpc": {"subsystemDescription": "Replication RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "vtl-rpc": {"subsystemDescription": "VTL RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas": {"subsystemDescription": "NAS", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "buffer-manager": {"subsystemDescription": "Buffer Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "res-mgr": {"subsystemDescription": "D2D Resource Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "d2d-iscsid": {"subsystemDescription": "ISCSI Daemon", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "fc-rpc": {"subsystemDescription": "Fiber Channel RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "smm": {"subsystemDescription": "Store Manager Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "licensing-rpc": {"subsystemDescription": "Licensing RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "rmc-ert-iscsid": {"subsystemDescription": "RMC ERT iSCSI Daemon", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas-bm": {"subsystemDescription": "NAS Buffer Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "d2d-manager-proxy": {"subsystemDescription": "D2D Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "replication": {"subsystemDescription": "Replication", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas-rpc": {"subsystemDescription": "NAS RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "smm-rpc": {"subsystemDescription": "SMM Thift RPC Service", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "cat-rpc": {"subsystemDescription": "Catalyst RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "predupe": {"subsystemDescription": "Predupe", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "object-store": {"subsystemDescription": "Object Store", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "vtl": {"subsystemDescription": "VTL", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}}, "overallHealthKey": "OverallHealth"}'
                ]
            ],
            [Service()],
        ),
    ],
)
def test_discover_storeonce4x_d2d_services(
    string_table: StringTable,
    expected_discoveries: Sequence[Service],
) -> None:
    section = parse_storeonce4x_d2d_services(string_table)
    result = list(discover_storeonce4x_d2d_services(section))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "string_table, expected_results",
    [
        (
            [
                [
                    '{"services": {"OverallHealth": {"subsystemDescription": "D2D Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "evt-mgr": {"subsystemDescription": "D2D Event Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas-share": {"subsystemDescription": "NAS Share Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "rep-obj-rpc": {"subsystemDescription": "RepObj RPC Server (FME)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "rep-rpc": {"subsystemDescription": "Replication RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "vtl-rpc": {"subsystemDescription": "VTL RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas": {"subsystemDescription": "NAS", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "buffer-manager": {"subsystemDescription": "Buffer Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "res-mgr": {"subsystemDescription": "D2D Resource Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "d2d-iscsid": {"subsystemDescription": "ISCSI Daemon", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "fc-rpc": {"subsystemDescription": "Fiber Channel RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "smm": {"subsystemDescription": "Store Manager Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "licensing-rpc": {"subsystemDescription": "Licensing RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "rmc-ert-iscsid": {"subsystemDescription": "RMC ERT iSCSI Daemon", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas-bm": {"subsystemDescription": "NAS Buffer Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "d2d-manager-proxy": {"subsystemDescription": "D2D Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "replication": {"subsystemDescription": "Replication", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas-rpc": {"subsystemDescription": "NAS RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "smm-rpc": {"subsystemDescription": "SMM Thift RPC Service", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "cat-rpc": {"subsystemDescription": "Catalyst RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "predupe": {"subsystemDescription": "Predupe", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "object-store": {"subsystemDescription": "Object Store", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "vtl": {"subsystemDescription": "VTL", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}}, "overallHealthKey": "OverallHealth"}'
                ]
            ],
            [
                Result(state=State.OK, summary="OverallHealth: Running (Active)"),
                Result(state=State.OK, summary="evt-mgr: Running (Active)"),
                Result(state=State.OK, summary="nas-share: Running (Active)"),
                Result(state=State.OK, summary="rep-obj-rpc: Running (Active)"),
                Result(state=State.OK, summary="rep-rpc: Running (Active)"),
                Result(state=State.OK, summary="vtl-rpc: Running (Active)"),
                Result(state=State.OK, summary="nas: Running (Active)"),
                Result(state=State.OK, summary="buffer-manager: Running (Active)"),
                Result(state=State.OK, summary="res-mgr: Running (Active)"),
                Result(state=State.OK, summary="d2d-iscsid: Running (Active)"),
                Result(state=State.OK, summary="fc-rpc: Running (Active)"),
                Result(state=State.OK, summary="smm: Running (Active)"),
                Result(state=State.OK, summary="licensing-rpc: Running (Active)"),
                Result(state=State.OK, summary="rmc-ert-iscsid: Running (Active)"),
                Result(state=State.OK, summary="nas-bm: Running (Active)"),
                Result(state=State.OK, summary="d2d-manager-proxy: Running (Active)"),
                Result(state=State.OK, summary="replication: Running (Active)"),
                Result(state=State.OK, summary="nas-rpc: Running (Active)"),
                Result(state=State.OK, summary="smm-rpc: Running (Active)"),
                Result(state=State.OK, summary="cat-rpc: Running (Active)"),
                Result(state=State.OK, summary="predupe: Running (Active)"),
                Result(state=State.OK, summary="object-store: Running (Active)"),
                Result(state=State.OK, summary="vtl: Running (Active)"),
            ],
        ),
    ],
)
def test_check_storeonce4x_d2d_services(
    string_table: StringTable,
    expected_results: Sequence[Result],
) -> None:
    section = parse_storeonce4x_d2d_services(string_table)
    result = list(check_storeonce4x_d2d_services(section))
    assert result == expected_results
