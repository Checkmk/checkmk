#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Iterable, Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.netapp import models
from cmk.plugins.netapp.lib.snapvault import DEFAULT_TRANSFER_STATE, DEFAULT_UNHEALTHY_STATE

# <<<netapp_ontap_snapvault:sep(0)>>>
# {
#     "destination": "mcc_darz_a_svm02_FC:rootvg_dest",
#     "lag_time": "PT23M46S",
#     "policy_name": "Asynchronous",
#     "policy_type": "async",
#     "source_svm_name": "mcc_darz_b_svm01_FC",
#     "state": "snapmirrored",
#     "transfer_state":"success",
# }
# {
#     "destination": "mcc_darz_a_svm02_FC:vol_data1vg_dest",
#     "lag_time": "PT23M46S",
#     "policy_name": "Asynchronous",
#     "policy_type": "async",
#     "source_svm_name": "mcc_darz_b_svm01_FC",
#     "state": "snapmirrored",
#     "transfer_state":"transferring",
# }

Section = Mapping[str, models.SnapMirrorModel]


def parse_netapp_ontap_snapmirror(string_table: StringTable) -> Section:
    return {
        snap.destination: snap
        for line in string_table
        for snap in [models.SnapMirrorModel.model_validate_json(line[0])]
    }


agent_section_netapp_ontap_volumes = AgentSection(
    name="netapp_ontap_snapvault",
    parse_function=parse_netapp_ontap_snapmirror,
)


def _prefilter_items(
    section: Section,
    exclude_vserver: bool,
) -> Iterable[tuple[str, models.SnapMirrorModel]]:
    if exclude_vserver:
        return [i for i in section.items() if ":" not in i[0]]
    return [i for i in section.items() if ":" in i[0]]


def discover_netapp_ontap_snapvault(
    params: Mapping[str, Any],
    section: Section,
) -> DiscoveryResult:
    for name, _ in _prefilter_items(section, params["exclude_destination_vserver"]):
        yield Service(item=name)


def check_netapp_ontap_snapvault(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    snapvault = section.get(item)
    if not snapvault:
        return

    if snapvault.source_svm_name:
        yield Result(state=State.OK, summary=f"Source-system: {snapvault.source_svm_name}")
    if snapvault.destination:
        yield Result(state=State.OK, summary=f"Destination-system: {snapvault.destination}")
    if snapvault.policy_name:
        yield Result(state=State.OK, summary=f"Policy: {snapvault.policy_name}")
    else:
        yield Result(state=State.OK, summary="Policy not set")

    if snapvault.transfer_state:
        yield Result(
            state=State(
                params["transfer_state"].get(snapvault.transfer_state, State.UNKNOWN.value)
            ),
            summary=f"Transfer State: {snapvault.transfer_state}",
        )

    if snapvault.state:
        yield Result(state=State.OK, summary=f"State: {snapvault.state}")

    if snapvault.healthy is False:
        reasons = ", ".join(snapvault.unhealthy_reason)
        yield Result(
            state=State(params["unhealthy_state"]),
            summary=f"Unhealthy: {reasons}" if reasons else "Unhealthy",
        )
    elif snapvault.healthy:
        yield Result(state=State.OK, notice="Healthy")

    if (lagtime := snapvault.lagtime()) is None:
        return

    policy_lag_time = {
        entry["policy_name"]: entry["levels"] for entry in params.get("policy_lag_time", [])
    }
    levels: LevelsT[float] = policy_lag_time.get(
        snapvault.policy_name, params.get("lag_time", ("no_levels", None))
    )

    yield from check_levels(
        value=lagtime,
        levels_upper=levels,
        render_func=render.timespan,
        label="Lag time",
    )


check_plugin_netapp_ontap_snapmirror = CheckPlugin(
    name="netapp_ontap_snapvault",
    service_name="Snapvault %s",
    discovery_function=discover_netapp_ontap_snapvault,
    discovery_ruleset_name="discovery_snapvault",
    discovery_default_parameters={"exclude_destination_vserver": False},
    check_function=check_netapp_ontap_snapvault,
    check_ruleset_name="snapvault",
    check_default_parameters={
        "transfer_state": DEFAULT_TRANSFER_STATE,
        "unhealthy_state": DEFAULT_UNHEALTHY_STATE,
    },
)
