#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_ha_manager_status import (
    check_proxmox_ve_ha_manager_status,
    discover_proxmox_ve_ha_manager_status,
    Params,
    parse_proxmox_ve_ha_manager_status,
)
from cmk.plugins.proxmox_ve.lib.ha_manager_status import (
    LrmNode,
    QuorumItem,
    SectionHaManagerCurrent,
    ServiceItem,
)

STRING_TABLE = [
    [
        '{"quorum": {"id": "quorum", "node": "pve-fra-002", "status": "OK", "type": "quorum"}, '
        '"lrm_nodes": {"pve-fra-001": {"node": "pve-fra-001", "status": "pve-fra-001 (idle, Fri Oct 10 10:20:04 2025)", '
        '"timestamp": 1760084404, "type": "lrm", "services": {"ct:137": {"node": "pve-fra-001", '
        '"comment": null, "sid": "ct:137", "state": "started", "type": "service"}, '
        '"vm:135": {"node": "pve-fra-001", "comment": null, "sid": "vm:135", '
        '"state": "started", "type": "service"}, "vm:162": {"node": "pve-fra-001", '
        '"comment": null, "sid": "vm:162", "state": "started", "type": "service"}}}, '
        '"pve-fra-002": {"node": "pve-fra-002", "status": "pve-fra-002 (maintenance, Fri Oct 10 10:20:08 2025)", '
        '"timestamp": 1760084408, "type": "lrm", "services": {"ct:128": {"node": "pve-fra-002", "comment": '
        '"internal DNS master - as important as fw.tribe29.com", "sid": "ct:128", "state": "started", "type": "service"}, '
        '"vm:104": {"node": "pve-fra-002", "comment": null, "sid": "vm:104", "state": "started", '
        '"type": "service"}, "vm:143": {"node": "pve-fra-002", "comment": null, "sid": "vm:143", '
        '"state": "error", "type": "service"}, "vm:182": {"node": "pve-fra-002", "comment": null, '
        '"sid": "vm:182", "state": "started", "type": "service"}}}, "pve-fra-003": {"node": "pve-fra-003", "status": '
        '"pve-fra-003 (active, Fri Oct 10 10:20:10 2025)", "timestamp": 1760084410, "type": "lrm", "services": '
        '{"vm:118": {"node": "pve-fra-003", "comment": null, "sid": "vm:118", "state": "something_else", "type": '
        '"service"}}}, "pve-fra-004": {"node": "pve-fra-004", "status": "pve-fra-004 (active, Fri Oct 10 10:20:04 2025)", '
        '"timestamp": 1760084404, "type": "lrm", "services": {"vm:126": {"node": "pve-fra-004", "comment": null, "sid": '
        '"vm:126", "state": "stopped", "type": "service"}, "vm:160": {"node": "pve-fra-004", "comment": null, '
        '"sid": "vm:160", "state": "ignored", "type": "service"}}}}}'
    ]
]

SECTION = SectionHaManagerCurrent(
    quorum=QuorumItem(id="quorum", node="pve-fra-002", status="OK", type="quorum"),
    lrm_nodes={
        "pve-fra-001": LrmNode(
            node="pve-fra-001",
            status="pve-fra-001 (idle, Fri Oct 10 10:20:04 2025)",
            timestamp=1760084404,
            type="lrm",
            services={
                "ct:137": ServiceItem(
                    node="pve-fra-001",
                    comment=None,
                    sid="ct:137",
                    state="started",
                    type="service",
                ),
                "vm:135": ServiceItem(
                    node="pve-fra-001",
                    comment=None,
                    sid="vm:135",
                    state="started",
                    type="service",
                ),
                "vm:162": ServiceItem(
                    node="pve-fra-001",
                    comment=None,
                    sid="vm:162",
                    state="started",
                    type="service",
                ),
            },
        ),
        "pve-fra-002": LrmNode(
            node="pve-fra-002",
            status="pve-fra-002 (maintenance, Fri Oct 10 10:20:08 2025)",
            timestamp=1760084408,
            type="lrm",
            services={
                "ct:128": ServiceItem(
                    node="pve-fra-002",
                    comment="internal DNS master - as important as fw.tribe29.com",
                    sid="ct:128",
                    state="started",
                    type="service",
                ),
                "vm:104": ServiceItem(
                    node="pve-fra-002",
                    comment=None,
                    sid="vm:104",
                    state="started",
                    type="service",
                ),
                "vm:143": ServiceItem(
                    node="pve-fra-002",
                    comment=None,
                    sid="vm:143",
                    state="error",
                    type="service",
                ),
                "vm:182": ServiceItem(
                    node="pve-fra-002",
                    comment=None,
                    sid="vm:182",
                    state="started",
                    type="service",
                ),
            },
        ),
        "pve-fra-003": LrmNode(
            node="pve-fra-003",
            status="pve-fra-003 (active, Fri Oct 10 10:20:10 2025)",
            timestamp=1760084410,
            type="lrm",
            services={
                "vm:118": ServiceItem(
                    node="pve-fra-003",
                    comment=None,
                    sid="vm:118",
                    state="something_else",
                    type="service",
                )
            },
        ),
        "pve-fra-004": LrmNode(
            node="pve-fra-004",
            status="pve-fra-004 (active, Fri Oct 10 10:20:04 2025)",
            timestamp=1760084404,
            type="lrm",
            services={
                "vm:126": ServiceItem(
                    node="pve-fra-004",
                    comment=None,
                    sid="vm:126",
                    state="stopped",
                    type="service",
                ),
                "vm:160": ServiceItem(
                    node="pve-fra-004",
                    comment=None,
                    sid="vm:160",
                    state="ignored",
                    type="service",
                ),
            },
        ),
    },
)

SECTION_NO_QUORUM = SectionHaManagerCurrent(
    quorum=None,
    lrm_nodes={},
)


def test_parse_proxmox_ve_ha_manager_status() -> None:
    assert parse_proxmox_ve_ha_manager_status(STRING_TABLE) == SECTION


def test_discover_proxmox_ve_ha_manager_status() -> None:
    assert list(discover_proxmox_ve_ha_manager_status(SECTION)) == [
        Service(item="quorum"),
        Service(item="pve-fra-001"),
        Service(item="pve-fra-002"),
        Service(item="pve-fra-003"),
        Service(item="pve-fra-004"),
    ]


@pytest.mark.parametrize(
    "item,params,section,expected_result",
    [
        pytest.param(
            "pve-fra-001",
            {"ignored_vms_state": 0, "stopped_vms_state": 0},
            SECTION_NO_QUORUM,
            [],
            id="No quorum - no results",
        ),
        pytest.param(
            "pve-fra-001",
            {"ignored_vms_state": 0, "stopped_vms_state": 0},
            SECTION,
            [
                Result(state=State.OK, summary="Quorum status: OK"),
                Result(state=State.OK, summary='Node "pve-fra-001" status: IDLE'),
                Result(state=State.OK, summary="Started: 2"),
            ],
            id="All OK. Node is idle. State for ignored and stopped VMs is OK",
        ),
        pytest.param(
            "pve-fra-002",
            {"ignored_vms_state": 0, "stopped_vms_state": 0},
            SECTION,
            [
                Result(state=State.OK, summary="Quorum status: OK"),
                Result(state=State.WARN, summary='Node "pve-fra-002" status: MAINTENANCE'),
                Result(state=State.OK, summary="Started: 2"),
                Result(state=State.CRIT, summary="Error: 1"),
            ],
            id="Node is in maintenance -> WARN. One VM with error -> CRIT",
        ),
        pytest.param(
            "pve-fra-003",
            {"ignored_vms_state": 0, "stopped_vms_state": 0},
            SECTION,
            [
                Result(state=State.OK, summary="Quorum status: OK"),
                Result(state=State.OK, summary='Node "pve-fra-003" status: ACTIVE'),
                Result(state=State.CRIT, summary="Something_else: 1"),
            ],
            id="Node active, VM in something_else state -> CRIT",
        ),
        pytest.param(
            "pve-fra-004",
            {"ignored_vms_state": 1, "stopped_vms_state": 2},
            SECTION,
            [
                Result(state=State.OK, summary="Quorum status: OK"),
                Result(state=State.OK, summary='Node "pve-fra-004" status: ACTIVE'),
                Result(state=State.CRIT, summary="Stopped: 1"),
                Result(state=State.WARN, summary="Ignored: 1"),
            ],
            id="Node active, one VM stopped (CRIT), one ignored (WARN) -> because of params",
        ),
    ],
)
def test_check_proxmox_ve_ha_manager_status(
    item: str,
    params: Params,
    section: SectionHaManagerCurrent,
    expected_result: CheckResult,
) -> None:
    assert list(check_proxmox_ve_ha_manager_status(item, params, section)) == expected_result
