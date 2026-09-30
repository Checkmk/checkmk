#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


@dataclass(frozen=True, kw_only=True)
class PerformanceExtent:
    name: str
    statuses: Sequence[str]


@dataclass(frozen=True, kw_only=True)
class VeeamScaleoutRepository:
    """Mirrors the VBR REST API's ScaleOutRepositoryModel
    (GET /api/v1/backupInfrastructure/scaleOutRepositories).

    `capacityTier`/`archiveTier` are optional at the top level (a scale-out
    repository may not have either configured), so their `isEnabled` flags are
    `None` rather than `False` in that case.
    """

    description: str
    performance_extents: Sequence[PerformanceExtent]
    capacity_tier_enabled: bool | None
    archive_tier_enabled: bool | None
    placement_policy_type: str


Section = Mapping[str, VeeamScaleoutRepository]


class CheckParameters(TypedDict):
    status_normal: int
    status_pending: int
    status_sealed: int
    status_evacuate: int
    status_maintenance: int
    status_resync_required: int
    status_tenant_evacuating: int
    no_extents_state: int


def parse_veeam_scaleout_repositories(string_table: StringTable) -> Section:
    section: dict[str, VeeamScaleoutRepository] = {}
    for line in string_table:
        repo_dict = json.loads(line[0])
        performance_tier = repo_dict["performanceTier"]
        extents = [
            PerformanceExtent(
                name=extent["name"],
                statuses=extent.get("status") or [],
            )
            for extent in performance_tier["performanceExtents"]
        ]
        capacity_tier = repo_dict.get("capacityTier")
        archive_tier = repo_dict.get("archiveTier")
        section[repo_dict["name"]] = VeeamScaleoutRepository(
            description=repo_dict["description"],
            performance_extents=extents,
            capacity_tier_enabled=(
                capacity_tier["isEnabled"] if capacity_tier is not None else None
            ),
            archive_tier_enabled=(archive_tier["isEnabled"] if archive_tier is not None else None),
            placement_policy_type=repo_dict["placementPolicy"]["type"],
        )
    return section


def discovery_veeam_scaleout_repositories(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def _status_state(status: str, params: CheckParameters) -> State:
    match status:
        case "Normal":
            return State(params["status_normal"])
        case "Pending":
            return State(params["status_pending"])
        case "Sealed":
            return State(params["status_sealed"])
        case "Evacuate":
            return State(params["status_evacuate"])
        case "Maintenance":
            return State(params["status_maintenance"])
        case "ResyncRequired":
            return State(params["status_resync_required"])
        case "TenantEvacuating":
            return State(params["status_tenant_evacuating"])
        case _:
            return State.UNKNOWN


def _extent_state(statuses: Sequence[str], params: CheckParameters) -> State:
    if not statuses:
        # TODO: an empty status list is assumed to mean the extent has no active
        # issues (treated as healthy). Double-check this assumption once we can
        # test against a real instance.
        return State.OK
    return State.worst(*(_status_state(status, params) for status in statuses))


def check_veeam_scaleout_repositories(
    item: str, params: CheckParameters, section: Section
) -> CheckResult:
    if (repo := section.get(item)) is None:
        return

    if not repo.performance_extents:
        yield Result(
            state=State(params["no_extents_state"]),
            summary="No performance extents configured",
        )
    else:
        problem_extents = []
        extent_states = []
        for extent in repo.performance_extents:
            state = _extent_state(extent.statuses, params)
            extent_states.append(state)
            if state != State.OK:
                problem_extents.append(f"{extent.name} ({', '.join(extent.statuses)})")

        count = len(repo.performance_extents)
        summary = f"{count} extent{'' if count == 1 else 's'}"
        if problem_extents:
            summary += f", {', '.join(problem_extents)}"
        yield Result(
            state=State.worst(*extent_states),
            summary=summary,
        )

        for extent in repo.performance_extents:
            yield Result(
                state=State.OK,
                notice=f"Extent {extent.name}: {', '.join(extent.statuses) or 'no status reported'}",
            )

    yield Result(
        state=State.OK,
        notice=f"Description: {repo.description or 'none'}",
    )
    if repo.capacity_tier_enabled is not None:
        yield Result(
            state=State.OK,
            notice=f"Capacity tier: {'enabled' if repo.capacity_tier_enabled else 'disabled'}",
        )
    if repo.archive_tier_enabled is not None:
        yield Result(
            state=State.OK,
            notice=f"Archive tier: {'enabled' if repo.archive_tier_enabled else 'disabled'}",
        )
    yield Result(
        state=State.OK,
        notice=f"Placement policy: {repo.placement_policy_type}",
    )


agent_section_veeam_scaleout_repositories = AgentSection(
    name="veeam_scaleout_repositories",
    parse_function=parse_veeam_scaleout_repositories,
)

check_plugin_veeam_scaleout_repositories = CheckPlugin(
    name="veeam_scaleout_repositories",
    service_name="Scale-out repository %s",
    discovery_function=discovery_veeam_scaleout_repositories,
    check_function=check_veeam_scaleout_repositories,
    check_ruleset_name="veeam_scaleout_repositories",
    check_default_parameters=CheckParameters(
        status_normal=0,
        status_pending=0,
        status_sealed=0,
        status_evacuate=1,
        status_maintenance=1,
        status_resync_required=1,
        status_tenant_evacuating=1,
        no_extents_state=1,
    ),
)
