#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.veeam.agent_based.veeam_scaleout_repositories import (
    check_veeam_scaleout_repositories,
    CheckParameters,
    discovery_veeam_scaleout_repositories,
    parse_veeam_scaleout_repositories,
    PerformanceExtent,
    VeeamScaleoutRepository,
)

PARAMS = CheckParameters(
    status_normal=0,
    status_pending=0,
    status_sealed=0,
    status_evacuate=1,
    status_maintenance=1,
    status_resync_required=1,
    status_tenant_evacuating=1,
    no_extents_state=1,
)


def _extent(name: str = "extent-1", status: list[str] | None = None) -> dict[str, object]:
    extent: dict[str, object] = {"id": "id-1", "name": name}
    if status is not None:
        extent["status"] = status
    return extent


def _scaleout_repo(name: str = "sobr-1", **overrides: object) -> str:
    repo_dict: dict[str, object] = {
        "id": "id-1",
        "name": name,
        "description": "Primary SOBR",
        "performanceTier": {"performanceExtents": [_extent(status=["Normal"])]},
        "placementPolicy": {"type": "DataLocality"},
    }
    repo_dict.update(overrides)
    return json.dumps(repo_dict)


def test_discovery_veeam_scaleout_repositories() -> None:
    section = parse_veeam_scaleout_repositories([[_scaleout_repo("sobr-1")]])
    assert list(discovery_veeam_scaleout_repositories(section)) == [Service(item="sobr-1")]


def test_parse_veeam_scaleout_repositories() -> None:
    section = parse_veeam_scaleout_repositories([[_scaleout_repo()]])
    assert section == {
        "sobr-1": VeeamScaleoutRepository(
            description="Primary SOBR",
            performance_extents=[PerformanceExtent(name="extent-1", statuses=["Normal"])],
            capacity_tier_enabled=None,
            archive_tier_enabled=None,
            placement_policy_type="DataLocality",
        )
    }


def test_parse_veeam_scaleout_repositories_with_capacity_and_archive_tier() -> None:
    section = parse_veeam_scaleout_repositories(
        [
            [
                _scaleout_repo(
                    capacityTier={"isEnabled": True},
                    archiveTier={"isEnabled": False},
                )
            ]
        ]
    )
    repo = section["sobr-1"]
    assert repo.capacity_tier_enabled is True
    assert repo.archive_tier_enabled is False


def test_check_veeam_scaleout_repositories_normal_is_ok() -> None:
    section = parse_veeam_scaleout_repositories([[_scaleout_repo()]])
    results = list(check_veeam_scaleout_repositories("sobr-1", PARAMS, section))
    assert results[0] == Result(state=State.OK, summary="1 extent")


def test_check_veeam_scaleout_repositories_maintenance_is_warn() -> None:
    section = parse_veeam_scaleout_repositories(
        [
            [
                _scaleout_repo(
                    performanceTier={"performanceExtents": [_extent(status=["Maintenance"])]}
                )
            ]
        ]
    )
    results = list(check_veeam_scaleout_repositories("sobr-1", PARAMS, section))
    assert results[0] == Result(state=State.WARN, summary="1 extent, extent-1 (Maintenance)")


def test_check_veeam_scaleout_repositories_unknown_status_is_unknown() -> None:
    section = parse_veeam_scaleout_repositories(
        [[_scaleout_repo(performanceTier={"performanceExtents": [_extent(status=["Kaputt"])]})]]
    )
    results = list(check_veeam_scaleout_repositories("sobr-1", PARAMS, section))
    assert results[0] == Result(state=State.UNKNOWN, summary="1 extent, extent-1 (Kaputt)")


def test_check_veeam_scaleout_repositories_empty_status_is_ok() -> None:
    section = parse_veeam_scaleout_repositories(
        [[_scaleout_repo(performanceTier={"performanceExtents": [_extent(status=[])]})]]
    )
    results = list(check_veeam_scaleout_repositories("sobr-1", PARAMS, section))
    assert results[0] == Result(state=State.OK, summary="1 extent")
    assert Result(state=State.OK, notice="Extent extent-1: no status reported") in results


def test_check_veeam_scaleout_repositories_no_extents_is_warn_by_default() -> None:
    section = parse_veeam_scaleout_repositories(
        [[_scaleout_repo(performanceTier={"performanceExtents": []})]]
    )
    results = list(check_veeam_scaleout_repositories("sobr-1", PARAMS, section))
    assert results[0] == Result(state=State.WARN, summary="No performance extents configured")


def test_check_veeam_scaleout_repositories_worst_of_multiple_extents() -> None:
    section = parse_veeam_scaleout_repositories(
        [
            [
                _scaleout_repo(
                    performanceTier={
                        "performanceExtents": [
                            _extent("extent-1", status=["Normal"]),
                            _extent("extent-2", status=["Evacuate"]),
                        ]
                    }
                )
            ]
        ]
    )
    results = list(check_veeam_scaleout_repositories("sobr-1", PARAMS, section))
    assert results[0] == Result(state=State.WARN, summary="2 extents, extent-2 (Evacuate)")


def test_check_veeam_scaleout_repositories_details() -> None:
    section = parse_veeam_scaleout_repositories(
        [
            [
                _scaleout_repo(
                    capacityTier={"isEnabled": True},
                    archiveTier={"isEnabled": False},
                )
            ]
        ]
    )
    results = list(check_veeam_scaleout_repositories("sobr-1", PARAMS, section))
    assert Result(state=State.OK, notice="Description: Primary SOBR") in results
    assert Result(state=State.OK, notice="Capacity tier: enabled") in results
    assert Result(state=State.OK, notice="Archive tier: disabled") in results
    assert Result(state=State.OK, notice="Placement policy: DataLocality") in results


def test_check_veeam_scaleout_repositories_omits_tier_details_when_not_configured() -> None:
    section = parse_veeam_scaleout_repositories([[_scaleout_repo()]])
    results = list(check_veeam_scaleout_repositories("sobr-1", PARAMS, section))
    assert not any(r.details.startswith("Capacity tier:") for r in results if isinstance(r, Result))
    assert not any(r.details.startswith("Archive tier:") for r in results if isinstance(r, Result))


def test_check_veeam_scaleout_repositories_vanished_item_yields_nothing() -> None:
    section = parse_veeam_scaleout_repositories([[_scaleout_repo("sobr-1")]])
    assert list(check_veeam_scaleout_repositories("sobr-2", PARAMS, section)) == []
