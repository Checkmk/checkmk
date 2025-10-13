#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.storeonce4x_d2d_services import (
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
            [(None, {})],
        ),
    ],
)
def test_discover_storeonce4x_d2d_services(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for storeonce4x_d2d_services check."""
    parsed = parse_storeonce4x_d2d_services(string_table)
    result = list(discover_storeonce4x_d2d_services(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                [
                    '{"services": {"OverallHealth": {"subsystemDescription": "D2D Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "evt-mgr": {"subsystemDescription": "D2D Event Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas-share": {"subsystemDescription": "NAS Share Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "rep-obj-rpc": {"subsystemDescription": "RepObj RPC Server (FME)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "rep-rpc": {"subsystemDescription": "Replication RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "vtl-rpc": {"subsystemDescription": "VTL RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas": {"subsystemDescription": "NAS", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "buffer-manager": {"subsystemDescription": "Buffer Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "res-mgr": {"subsystemDescription": "D2D Resource Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "d2d-iscsid": {"subsystemDescription": "ISCSI Daemon", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "fc-rpc": {"subsystemDescription": "Fiber Channel RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "smm": {"subsystemDescription": "Store Manager Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "licensing-rpc": {"subsystemDescription": "Licensing RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "rmc-ert-iscsid": {"subsystemDescription": "RMC ERT iSCSI Daemon", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas-bm": {"subsystemDescription": "NAS Buffer Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "d2d-manager-proxy": {"subsystemDescription": "D2D Manager", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "replication": {"subsystemDescription": "Replication", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "nas-rpc": {"subsystemDescription": "NAS RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "smm-rpc": {"subsystemDescription": "SMM Thift RPC Service", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "cat-rpc": {"subsystemDescription": "Catalyst RPC Server (Thrift)", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "predupe": {"subsystemDescription": "Predupe", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "object-store": {"subsystemDescription": "Object Store", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}, "vtl": {"subsystemDescription": "VTL", "subsystemState": "Active", "health": 15, "healthString": "Running", "healthLevelString": "OK", "healthLevel": 1}}, "overallHealthKey": "OverallHealth"}'
                ]
            ],
            [
                (0, "OverallHealth: Running (Active)"),
                (0, "evt-mgr: Running (Active)"),
                (0, "nas-share: Running (Active)"),
                (0, "rep-obj-rpc: Running (Active)"),
                (0, "rep-rpc: Running (Active)"),
                (0, "vtl-rpc: Running (Active)"),
                (0, "nas: Running (Active)"),
                (0, "buffer-manager: Running (Active)"),
                (0, "res-mgr: Running (Active)"),
                (0, "d2d-iscsid: Running (Active)"),
                (0, "fc-rpc: Running (Active)"),
                (0, "smm: Running (Active)"),
                (0, "licensing-rpc: Running (Active)"),
                (0, "rmc-ert-iscsid: Running (Active)"),
                (0, "nas-bm: Running (Active)"),
                (0, "d2d-manager-proxy: Running (Active)"),
                (0, "replication: Running (Active)"),
                (0, "nas-rpc: Running (Active)"),
                (0, "smm-rpc: Running (Active)"),
                (0, "cat-rpc: Running (Active)"),
                (0, "predupe: Running (Active)"),
                (0, "object-store: Running (Active)"),
                (0, "vtl: Running (Active)"),
            ],
        ),
    ],
)
def test_check_storeonce4x_d2d_services(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for storeonce4x_d2d_services check."""
    parsed = parse_storeonce4x_d2d_services(string_table)
    result = list(check_storeonce4x_d2d_services(item, params, parsed))
    assert result == expected_results
