#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.netapp import models
from cmk.plugins.netapp.agent_based.lib import filter_metrocluster_items

VolumesSection = Mapping[str, models.VolumeModel]
SvmSection = Mapping[str, models.SvmModel]


# <<<netapp_ontap_volumes:sep(0)>>>
# {
#     "files_maximum": 21251126,
#     "files_used": 97,
#     "logical_enforcement": false,
#     "logical_used": 1658880,
#     "msid": 2147484705,
#     "name": "Test_300T",
#     "snapshot_reserve_percent": 0,
#     "snapshot_reserve_size": 0,
#     "snapshot_used": 204800,
#     "space_available": 12804564213760,
#     "space_total": 329853488332800,
#     "state": "online",
#     "svm_name": "FlexPodXCS_NFS_Frank",
#     "svm_uuid": "208cfe14-c334-11ed-afdc-00a098c50e5b",
#     "uuid": "00b3e6b1-5781-11ee-b0c8-00a098c54c0b",
# }
# {
#     "files_maximum": 31122,
#     "files_used": 101,
#     "logical_enforcement": false,
#     "logical_used": 454656,
#     "msid": 2147484684,
#     "name": "svm_ansible_01_jl_root",
#     "snapshot_reserve_percent": 5,
#     "snapshot_reserve_size": 53686272,
#     "snapshot_used": 0,
#     "space_available": 1019600896,
#     "space_total": 1020055552,
#     "state": "online",
#     "svm_name": "svm_ansible_01_jl",
#     "svm_uuid": "00bd0f4e-27ac-11ee-8516-00a098c50e5b",
#     "uuid": "0125d89f-27ac-11ee-8516-00a098c50e5b",
# }


def discover_netapp_ontap_snapshots(
    section_netapp_ontap_volumes: VolumesSection | None,
    section_netapp_ontap_vs_status: SvmSection | None,
) -> DiscoveryResult:
    if section_netapp_ontap_volumes and section_netapp_ontap_vs_status:
        section_netapp_ontap_volumes = filter_metrocluster_items(
            section_netapp_ontap_volumes, section_netapp_ontap_vs_status
        )
        yield from (Service(item=item) for item in section_netapp_ontap_volumes)


def check_netapp_ontap_snapshots(
    item: str,
    params: Mapping[str, Any],
    section_netapp_ontap_volumes: VolumesSection | None,
    section_netapp_ontap_vs_status: SvmSection | None,
) -> CheckResult:
    if not section_netapp_ontap_volumes:
        return

    volume = section_netapp_ontap_volumes.get(item)

    if not volume:
        return

    if volume.state != "online" or volume.snapshot_used is None or volume.space_total is None:
        yield Result(
            state=State.UNKNOWN,
            summary=f"No snapshot information available. Volume state is {volume.state}",
        )
        return

    if not volume.snapshot_reserve_size:
        yield Result(
            state=State.OK, summary=f"Used snapshot space: {render.bytes(volume.snapshot_used)}"
        )
        yield Metric("bytes", volume.snapshot_used)
        yield Result(
            state=State(params.get("state_noreserve", State.WARN)),
            summary="No snapshot reserve configured",
        )
        return

    used_percent = (volume.snapshot_used / volume.snapshot_reserve_size) * 100.0
    snapshot_used = volume.snapshot_used

    yield from check_levels_v1(
        used_percent,
        levels_upper=params.get("levels"),
        label="Reserve used",
        render_func=lambda v: f"{v:.1f}% ({render.bytes(snapshot_used)})",
    )

    volume_total = volume.space_total + volume.snapshot_reserve_size
    yield Result(
        state=State.OK,
        summary=f"Total Reserve: {volume.snapshot_reserve_percent}% ({render.bytes(volume.snapshot_reserve_size)}) of {render.bytes(volume_total)}",
    )
    yield Metric(
        name="bytes", value=volume.snapshot_used, boundaries=(0, volume.snapshot_reserve_size)
    )


check_plugin_netapp_ontap_shanpshots = CheckPlugin(
    name="netapp_ontap_snapshots",
    service_name="Snapshots Volume %s",
    sections=["netapp_ontap_volumes", "netapp_ontap_vs_status"],
    discovery_function=discover_netapp_ontap_snapshots,
    check_function=check_netapp_ontap_snapshots,
    check_ruleset_name="netapp_snapshots",
    check_default_parameters={"levels": (85.0, 90.0)},
)
