#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Sequence

from cmk.agent_based.v2 import all_of, any_of, exists, startswith

FSBlock = tuple[str, float, float, str]
FSBlocks = Sequence[FSBlock]

DETECT = any_of(
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11096.6"),
    # e.g. HM800 report "linux" as type. Check the vendor tree too
    all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        exists(".1.3.6.1.4.1.11096.6.1.*"),
    ),
)

STATUS_MAP = {
    "1": "unformatted",
    "2": "mounted",
    "3": "formatted",
    "4": "needsChecking",
}


def parse_physical_volumes(volume_data: Iterable) -> tuple[dict, dict]:
    map_label = {}
    parsed_volumes = {}

    for volume_id, label, status_id, size, avail, evs in volume_data:
        if volume_id == "":
            continue

        map_label[volume_id] = label

        volume = f"{volume_id} {label}"
        status = STATUS_MAP.get(status_id, "unidentified")
        size_mb = int(size) / 1048576.0 if size else None
        avail_mb = int(avail) / 1048576.0 if avail else None
        parsed_volumes[volume] = (status, size_mb, avail_mb, evs)

    return map_label, parsed_volumes


def parse_virtual_volumes(map_label: dict, virtual_volumes: Iterable, quotas: Iterable) -> dict:
    # Note: A virtual volume may have no quota or a quota without a limit
    # and usage.
    # Besides quotas for virtual volumes the quota table also contains
    # user and group quotas.

    def quota_oid_end(phys_volume_id: str, virtual_volume_oid_end: str) -> str:
        """A QuotasEntry is indexed by a concatenation of the physical
        volume_id the virtual volume belongs to and the oid_end without
        the first element of the virtual volume."""
        return ".".join([phys_volume_id] + virtual_volume_oid_end.split(".")[1:] + ["0"])

    parsed: dict[str, tuple[float | None, float | None]] = {}
    map_quota_oid: dict = {}
    for oid_end, phys_volume_id, virtual_volume_label in virtual_volumes:
        phys_volume_label = map_label[phys_volume_id]
        volume = f"{virtual_volume_label} on {phys_volume_label}"
        parsed[volume] = None, None

        ref_oid_end = quota_oid_end(phys_volume_id, oid_end)
        map_quota_oid[ref_oid_end] = volume

    volume_quota = "3"
    for oid_end, quota_type, usage, limit in quotas:
        if quota_type != volume_quota:
            continue

        if usage and limit:
            volume = map_quota_oid[oid_end]
            size_mb = int(limit) / 1048576.0
            avail_mb = size_mb - int(usage) / 1048576.0
            parsed[volume] = (size_mb, avail_mb)
        else:
            parsed[volume] = (None, None)

    return parsed
