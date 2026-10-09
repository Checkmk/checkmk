#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.veeam.lib import parse_iso8601_epoch


@dataclass(frozen=True, kw_only=True)
class VeeamReplica:
    """Mirrors the VBR REST API's RegularReplicaModel (GET /api/v1/replicas)."""

    id: str
    type: str
    platform_name: str
    state: str
    creation_time: float | None
    job_id: str


Section = Mapping[str, VeeamReplica]
"""The replicas per item: the name followed by the first 8 characters of the ID, since
replica names are not unique in Veeam."""

type CheckParameters = Mapping[str, int]
"""The monitoring state per replica state, keyed by the replica's `state` as the API
reports it (EReplicaState in the REST API schema, 1.3-rev1)."""

DEFAULT_PARAMETERS: CheckParameters = {
    "Ready": State.OK.value,
    "Processing": State.OK.value,
    "SureBackup": State.OK.value,
    "Failover": State.WARN.value,
    "FailedFailover": State.CRIT.value,
    "PermanentFailover": State.WARN.value,
    "Failback": State.WARN.value,
    "ReadyToSwitch": State.WARN.value,
}


def parse_veeam_replicas(string_table: StringTable) -> Section:
    section: dict[str, VeeamReplica] = {}
    for line in string_table:
        replica = json.loads(line[0])
        if replica["type"] != "Regular":
            continue
        section[f"{replica['name']} ({replica['id'][:8]})"] = VeeamReplica(
            id=replica["id"],
            type=replica["type"],
            platform_name=replica["platformName"],
            state=replica["state"],
            creation_time=parse_iso8601_epoch(replica["creationTime"]),
            job_id=replica["jobId"],
        )
    return section


def discovery_veeam_replicas(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_veeam_replicas(item: str, params: CheckParameters, section: Section) -> CheckResult:
    if (replica := section.get(item)) is None:
        return

    summary = f"{replica.platform_name} replica, {replica.state}"
    if (monitoring_state := params.get(replica.state)) is None:
        yield Result(
            state=State.UNKNOWN,
            summary=summary,
            details=f"Unrecognized replica state: {replica.state}",
        )
    else:
        yield Result(state=State(monitoring_state), summary=summary)

    yield Result(state=State.OK, notice=f"Type: {replica.type}")
    yield Result(state=State.OK, notice=f"Platform: {replica.platform_name}")
    yield Result(state=State.OK, notice=f"Source job ID: {replica.job_id}")
    if replica.creation_time is not None:
        yield Result(state=State.OK, notice=f"Created: {render.datetime(replica.creation_time)}")
    yield Result(state=State.OK, notice=f"Replica ID: {replica.id}")


agent_section_veeam_replicas = AgentSection(
    name="veeam_replicas",
    parse_function=parse_veeam_replicas,
)

check_plugin_veeam_replicas = CheckPlugin(
    name="veeam_replicas",
    service_name="Replica %s",
    discovery_function=discovery_veeam_replicas,
    check_function=check_veeam_replicas,
    check_ruleset_name="veeam_replicas",
    check_default_parameters=DEFAULT_PARAMETERS,
)
