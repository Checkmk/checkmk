#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    NoLevelsT,
    Result,
    Service,
    State,
)
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_replication import (
    _check_replications_with_no_errors,
    check_proxmox_ve_replication,
    discover_proxmox_ve_replication,
    Params,
)
from cmk.plugins.proxmox_ve.lib.replication import Replication, SectionReplication

SECTION_NO_REPLICATIONS = SectionReplication(
    node="node1",
    replications=[],
    cluster_has_replications=True,
)

SECTION_CLUSTER_NO_REPLICATIONS = SectionReplication(
    node="node1",
    replications=[],
    cluster_has_replications=False,
)

SECTION_WITH_ONE_ERROR = SectionReplication(
    node="node1",
    replications=[
        Replication(
            id="r1",
            source="local-lvm:vm-100-disk-1",
            target="node2",
            schedule="*/5 * * * *",
            last_sync=1700000000,
            last_try=1700000300,
            next_sync=1700000600,
            duration=300.0,
            error="Connection timed out",
        ),
    ],
    cluster_has_replications=True,
)

SECTION_WITH_TWO_ERRORS = SectionReplication(
    node="node1",
    replications=[
        Replication(
            id="r1",
            source="local-lvm:vm-100-disk-1",
            target="node2",
            schedule="*/5 * * * *",
            last_sync=1700000000,
            last_try=1700000300,
            next_sync=1700000600,
            duration=300.0,
            error="Connection timed out",
        ),
        Replication(
            id="r2",
            source="local-lvm:vm-100-disk-1",
            target="node2",
            schedule="*/5 * * * *",
            last_sync=1700000000,
            last_try=1700000300,
            next_sync=1700000600,
            duration=300.0,
            error="Another issue",
        ),
    ],
    cluster_has_replications=True,
)

SECTION_WITH_ONE_REPLICATION = SectionReplication(
    node="node1",
    replications=[
        Replication(
            id="r1",
            source="local-lvm:vm-100-disk-1",
            target="node2",
            schedule="*/5 * * * *",
            last_sync=1700000000,
            last_try=1700000300,
            next_sync=1700000600,
            duration=300.0,
            error=None,
        ),
    ],
    cluster_has_replications=True,
)


@pytest.mark.parametrize(
    "section,expected_discovery_result",
    [
        pytest.param(
            SECTION_NO_REPLICATIONS,
            [Service()],
            id="No Replications, but cluster has replications",
        ),
        pytest.param(
            SECTION_CLUSTER_NO_REPLICATIONS,
            [Service()],
            id="Cluster has no replications",
        ),
        pytest.param(
            SECTION_WITH_ONE_ERROR,
            [Service()],
            id="No Replications, but cluster has replications",
        ),
        pytest.param(
            SECTION_WITH_ONE_REPLICATION,
            [Service()],
            id="Cluster has no replications",
        ),
    ],
)
def test_discover_proxmox_ve_replication(
    section: SectionReplication,
    expected_discovery_result: DiscoveryResult,
) -> None:
    assert list(discover_proxmox_ve_replication(section)) == expected_discovery_result


@pytest.mark.parametrize(
    "params,section,expected_result",
    [
        pytest.param(
            {
                "time_since_last_replication": ("no_levels", None),
                "no_replications_state": 2,
            },
            SECTION_CLUSTER_NO_REPLICATIONS,
            [Result(state=State.CRIT, summary="Replication jobs not configured")],
            id="Cluster has no replications. CRIT, because of params",
        ),
        pytest.param(
            {
                "time_since_last_replication": ("no_levels", None),
                "no_replications_state": 2,
            },
            SECTION_NO_REPLICATIONS,
            [Result(state=State.OK, summary="No replication jobs found")],
            id="Cluster has replications, but none configured -> OK",
        ),
        pytest.param(
            {
                "time_since_last_replication": ("no_levels", None),
                "no_replications_state": 2,
            },
            SECTION_WITH_ONE_ERROR,
            [
                Result(
                    state=State.CRIT,
                    summary="Replication job: r1: Connection timed out",
                    details=None,
                )
            ],
            id="One replication with error -> CRIT",
        ),
        pytest.param(
            {
                "time_since_last_replication": ("no_levels", None),
                "no_replications_state": 2,
            },
            SECTION_WITH_TWO_ERRORS,
            [
                Result(
                    state=State.CRIT,
                    summary="Replication job: r1: Connection timed out",
                    details="r2: Another issue",
                )
            ],
            id="Two replications with errors -> CRIT",
        ),
    ],
)
def test_check_proxmox_ve_replication(
    params: Params,
    section: SectionReplication,
    expected_result: CheckResult,
) -> None:
    assert list(check_proxmox_ve_replication(params, section)) == expected_result


@pytest.mark.parametrize(
    "upper_levels,section,expected_result",
    [
        pytest.param(
            ("no_levels", None),
            SECTION_WITH_ONE_REPLICATION,
            [
                Result(state=State.OK, summary="All replications OK"),
                Result(
                    state=State.OK,
                    summary="Time since last replication: 2 minutes 0 seconds",
                ),
            ],
            id="One replication, no levels -> OK",
        ),
        pytest.param(
            ("fixed", (120, 240)),
            SECTION_WITH_ONE_REPLICATION,
            [
                Result(state=State.OK, summary="All replications OK"),
                Result(
                    state=State.WARN,
                    summary="Time since last replication: 2 minutes 0 seconds (warn/crit at 2 minutes 0 seconds/4 minutes 0 seconds)",
                ),
            ],
            id="One replication, fixed levels -> WARN",
        ),
    ],
)
def test_check_replications_with_no_errors(
    upper_levels: FixedLevelsT[float] | NoLevelsT,
    section: SectionReplication,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            _check_replications_with_no_errors(
                now=1700000120,
                replications=section.replications,
                upper_levels=upper_levels,
            )
        )
        == expected_result
    )
