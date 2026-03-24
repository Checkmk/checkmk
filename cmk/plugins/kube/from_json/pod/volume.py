# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import NotRequired, TypedDict

from ...schemata import api


class JSONPodVolumePersistentVolumeClaim(TypedDict):
    claimName: str
    readOnly: NotRequired[bool]


class JSONPodVolume(TypedDict):
    name: str
    persistentVolumeClaim: NotRequired[JSONPodVolumePersistentVolumeClaim]


def parse_pod_volume(volume: JSONPodVolume) -> api.Volume:
    pvc_source: api.VolumePersistentVolumeClaimSource | None = None
    if pvc := volume.get("persistentVolumeClaim"):
        pvc_source = api.VolumePersistentVolumeClaimSource(
            claim_name=pvc["claimName"], read_only=pvc.get("readOnly")
        )

    return api.Volume(name=api.VolumeName(volume["name"]), persistent_volume_claim=pvc_source)


def parse_pod_volumes(volumes: Sequence[JSONPodVolume]) -> Sequence[api.Volume]:
    return [parse_pod_volume(volume) for volume in volumes]
