#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import time
from typing import Any, Iterator, Mapping, MutableMapping

from .agent_based_api.v1 import get_value_store, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.df import (
    df_check_filesystem_single,
    FILESYSTEM_DEFAULT_LEVELS,
    MAGIC_FACTOR_DEFAULT_PARAMS,
    TREND_DEFAULT_PARAMS,
)
from .utils.kube import (
    AttachedPersistentVolumes,
    AttachedVolume,
    PersistentVolume,
    PersistentVolumeClaim,
    PersistentVolumeClaimAttachedVolumes,
    PersistentVolumeClaimPhase,
    PersistentVolumeClaims,
)

VOLUME_DEFAULT_PARAMS: Mapping[str, Any] = {
    **FILESYSTEM_DEFAULT_LEVELS,
    **MAGIC_FACTOR_DEFAULT_PARAMS,
    **TREND_DEFAULT_PARAMS,
}


def parse_persistent_volume_claims(string_table: StringTable) -> PersistentVolumeClaims:
    """Parses `string_table` into a PersistentVolumeClaims instance"""
    return PersistentVolumeClaims(**json.loads(string_table[0][0]))


def parse_persistent_volume_claims_attached_volumes(
    string_table: StringTable,
) -> PersistentVolumeClaimAttachedVolumes:
    """Parses `string_table` into a PersistentVolumeAttachedVolumes instance"""
    return PersistentVolumeClaimAttachedVolumes(**json.loads(string_table[0][0]))


def parse_attached_persistent_volumes(
    string_table: StringTable,
) -> AttachedPersistentVolumes:
    """Parses `string_table` into a PersistentVolumeClaimAttachedPersistentVolumes instance"""
    return AttachedPersistentVolumes.parse_raw(string_table[0][0])


register.agent_section(
    name="kube_pvc_v1",
    parse_function=parse_persistent_volume_claims,
    parsed_section_name="kube_pvc",
)


register.agent_section(
    name="kube_pvc_volumes_v1",
    parse_function=parse_persistent_volume_claims_attached_volumes,
    parsed_section_name="kube_pvc_volumes",
)

register.agent_section(
    name="kube_pvc_pvs_v1",
    parse_function=parse_attached_persistent_volumes,
    parsed_section_name="kube_pvc_pvs",
)


def discovery_kube_pvc(
    section_kube_pvc: PersistentVolumeClaims | None,
    section_kube_pvc_volumes: PersistentVolumeClaimAttachedVolumes | None,
    section_kube_pvc_pvs: AttachedPersistentVolumes | None,
) -> DiscoveryResult:
    if section_kube_pvc is None:
        return
    yield from (Service(item=pvc) for pvc in section_kube_pvc.claims.keys())


def check_kube_pvc(
    item: str,
    params: Mapping[str, Any],
    section_kube_pvc: PersistentVolumeClaims | None,
    section_kube_pvc_volumes: PersistentVolumeClaimAttachedVolumes | None,
    section_kube_pvc_pvs: AttachedPersistentVolumes | None,
) -> CheckResult:
    if section_kube_pvc is None or (pvc := section_kube_pvc.claims.get(item)) is None:
        return

    volume: AttachedVolume | None = (
        section_kube_pvc_volumes.volumes.get(item) if section_kube_pvc_volumes is not None else None
    )
    persistent_volume: PersistentVolume | None = (
        section_kube_pvc_pvs.volumes.get(pvc.volume_name)
        if section_kube_pvc_pvs and pvc.volume_name
        else None
    )
    yield from _check_kube_pvc(
        item=item,
        params=params,
        value_store=get_value_store(),
        pvc=pvc,
        persistent_volume=persistent_volume,
        volume=volume,
        timestamp=time.time(),
    )


def _check_kube_pvc(
    item: str,
    params: Mapping[str, Any],
    value_store: MutableMapping[str, Any],
    pvc: PersistentVolumeClaim,
    persistent_volume: PersistentVolume | None,
    volume: AttachedVolume | None,
    timestamp: None | float,
) -> CheckResult:

    if (status_phase := pvc.status.phase) is None:
        yield Result(state=State.CRIT, summary="Status: not reported")
        return

    yield from _output_status_and_pv_details(status_phase, persistent_volume)

    if volume is None:
        yield from _output_status_capacity_result(pvc)
        return

    yield from df_check_filesystem_single(
        value_store=value_store,
        mountpoint=item,
        filesystem_size=volume.capacity / 1024**2,
        free_space=volume.free / 1024**2,
        reserved_space=0.0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
        this_time=timestamp,
    )


def _output_status_and_pv_details(
    status_phase: PersistentVolumeClaimPhase, persistent_volume: PersistentVolume | None
) -> Iterator[Result]:
    status_output = f"Status: {status_phase.value}"
    yield Result(state=State.OK, summary=status_output)

    if status_phase is not PersistentVolumeClaimPhase.CLAIM_BOUND or persistent_volume is None:
        return

    yield from (
        Result(state=State.OK, notice=detail)
        for detail in (
            f"StorageClass: {persistent_volume.spec.storage_class_name}",
            f"Access Modes: {', '.join(mode.value for mode in persistent_volume.spec.access_modes)}",
            f"VolumeMode: {persistent_volume.spec.volume_mode}",
            f"Mounted Volume: {persistent_volume.name}",
        )
    )


def _output_status_capacity_result(pvc: PersistentVolumeClaim) -> Iterator[Result]:
    if (capacity := pvc.status.capacity) is not None and capacity.storage is not None:
        capacity_summary = f"Capacity: {render.bytes(capacity.storage)}"
    else:
        capacity_summary = "Capacity: not reported"
    yield Result(state=State.OK, summary=capacity_summary)


register.check_plugin(
    name="kube_pvc",
    service_name="Persistent Volume Claim %s",
    sections=[
        "kube_pvc",
        "kube_pvc_volumes",
        "kube_pvc_pvs",
    ],
    discovery_function=discovery_kube_pvc,
    check_function=check_kube_pvc,
    check_ruleset_name="kube_pvc",
    check_default_parameters=VOLUME_DEFAULT_PARAMS,
)
