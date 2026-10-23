#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.veeam.agent_based.veeam_replicas import (
    check_veeam_replicas,
    DEFAULT_PARAMETERS,
    discovery_veeam_replicas,
    parse_veeam_replicas,
)

_ID = "5f3a9c2e-8b1d-4e7a-9c3f-2d6b1a0e4f71"
_ITEM = "vm-1_replica (5f3a9c2e)"


def _replica(name: str = "vm-1_replica", **overrides: object) -> list[str]:
    replica: dict[str, object] = {
        "id": _ID,
        "name": name,
        "type": "Regular",
        "jobId": "job-id-1",
        "platformName": "VMware",
        "platformId": "platform-1",
        "creationTime": "2026-10-01T09:00:00+00:00",
        "state": "Ready",
    }
    replica.update(overrides)
    return [json.dumps(replica)]


def _cdp_replica(name: str) -> list[str]:
    return [
        json.dumps(
            {
                "id": "id-2",
                "name": name,
                "type": "CDP",
                "jobId": "job-id-2",
                "platformName": "VMware",
            }
        )
    ]


def test_discovery_veeam_replicas() -> None:
    section = parse_veeam_replicas(
        [
            _replica("vm-1_replica"),
            _replica("vm-2_replica", id="c4e8f1a7-6d2b-4a9e-b3c5-1f7d9e2a6b84"),
        ]
    )

    assert list(discovery_veeam_replicas(section)) == [
        Service(item=_ITEM),
        Service(item="vm-2_replica (c4e8f1a7)"),
    ]


def test_cdp_replicas_are_not_discovered() -> None:
    section = parse_veeam_replicas([_replica("vm-1_replica"), _cdp_replica("vm-2_cdp")])

    assert list(discovery_veeam_replicas(section)) == [Service(item=_ITEM)]


@pytest.mark.parametrize(
    "replica_state, expected",
    [
        pytest.param("Ready", State.OK, id="ready"),
        pytest.param("Processing", State.OK, id="processing"),
        pytest.param("SureBackup", State.OK, id="SureBackup test"),
        pytest.param("Failover", State.WARN, id="failover"),
        pytest.param("PermanentFailover", State.WARN, id="permanent failover"),
        pytest.param("Failback", State.WARN, id="failback"),
        pytest.param("ReadyToSwitch", State.WARN, id="ready to switch"),
        pytest.param("FailedFailover", State.CRIT, id="failed failover"),
    ],
)
def test_replica_state_is_mapped_by_default(replica_state: str, expected: State) -> None:
    section = parse_veeam_replicas([_replica(state=replica_state)])

    results = list(check_veeam_replicas(_ITEM, DEFAULT_PARAMETERS, section))

    assert results[0] == Result(state=expected, summary=f"VMware replica, {replica_state}")


def test_replica_state_mapping_is_configurable() -> None:
    section = parse_veeam_replicas([_replica(state="Failover")])
    params = {**DEFAULT_PARAMETERS, "Failover": State.OK.value}

    results = list(check_veeam_replicas(_ITEM, params, section))

    assert results[0] == Result(state=State.OK, summary="VMware replica, Failover")


def test_unrecognized_replica_state_is_unknown() -> None:
    section = parse_veeam_replicas([_replica(state="SomethingNew")])

    results = list(check_veeam_replicas(_ITEM, DEFAULT_PARAMETERS, section))

    assert results[0] == Result(
        state=State.UNKNOWN,
        summary="VMware replica, SomethingNew",
        details="Unrecognized replica state: SomethingNew",
    )


def test_replica_details_show_type_platform_job_and_creation() -> None:
    section = parse_veeam_replicas([_replica()])

    results = list(check_veeam_replicas(_ITEM, DEFAULT_PARAMETERS, section))

    assert results[1:4] == [
        Result(state=State.OK, notice="Type: Regular"),
        Result(state=State.OK, notice="Platform: VMware"),
        Result(state=State.OK, notice="Source job ID: job-id-1"),
    ]
    assert isinstance(created := results[4], Result)
    assert created.state is State.OK and created.details.startswith("Created: 2026-10-01")


def test_replica_details_show_the_replica_id() -> None:
    section = parse_veeam_replicas([_replica()])

    results = list(check_veeam_replicas(_ITEM, DEFAULT_PARAMETERS, section))

    assert Result(state=State.OK, notice=f"Replica ID: {_ID}") in results


def test_unparsable_creation_time_is_left_out() -> None:
    section = parse_veeam_replicas([_replica(creationTime="garbage")])

    results = list(check_veeam_replicas(_ITEM, DEFAULT_PARAMETERS, section))

    assert not any(isinstance(r, Result) and r.details.startswith("Created:") for r in results)


def test_replicas_sharing_a_name_are_discovered_separately() -> None:
    section = parse_veeam_replicas(
        [
            _replica(id="5f3a9c2e-8b1d-4e7a-9c3f-2d6b1a0e4f71"),
            _replica(id="b71d04a9-3c2e-4f1a-8d6b-9e0a7c5f2b13"),
        ]
    )

    assert list(discovery_veeam_replicas(section)) == [
        Service(item="vm-1_replica (5f3a9c2e)"),
        Service(item="vm-1_replica (b71d04a9)"),
    ]


def test_vanished_replica_yields_nothing() -> None:
    section = parse_veeam_replicas([_replica("vm-1_replica")])

    assert list(check_veeam_replicas("vm-2_replica (5f3a9c2e)", DEFAULT_PARAMETERS, section)) == []
