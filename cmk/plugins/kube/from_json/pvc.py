# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import NotRequired, TypedDict

from ..schemata import api
from ..util import map_optional
from .metadata import _metadata_from_json, JSONObjectWithMetadata
from .resources import JSONResourceRequirement, JSONResourceRequirements


class JSONPVCSpec(TypedDict):
    accessModes: NotRequired[Sequence[str]]
    resources: NotRequired[JSONResourceRequirements]
    storageClassName: NotRequired[str]
    volumeMode: NotRequired[str]
    volumeName: NotRequired[str]


class JSONPVCStatus(TypedDict):
    phase: NotRequired[str]
    accessModes: NotRequired[Sequence[str]]
    capacity: NotRequired[JSONResourceRequirement]
    currentVolumeAttributesClassName: NotRequired[str]


class JSONPersistentVolumeClaim(JSONObjectWithMetadata):
    spec: JSONPVCSpec
    status: JSONPVCStatus


class JSONPersistentVolumeClaimList(TypedDict):
    items: Sequence[JSONPersistentVolumeClaim]


def pvc_spec_from_json(pvc_spec: JSONPVCSpec) -> api.PersistentVolumeClaimSpec:
    access_modes = map_optional(
        lambda modes: [api.AccessMode(mode) for mode in modes], pvc_spec.get("accessModes")
    )
    resources = map_optional(
        api.StorageResourceRequirements.model_validate, pvc_spec.get("resources")
    )
    volume_mode = map_optional(api.PersistentVolumeMode, pvc_spec.get("volumeMode"))
    volume_name = map_optional(api.VolumeName, pvc_spec.get("volumeName"))

    return api.PersistentVolumeClaimSpec(
        access_modes=access_modes,
        resources=resources,
        storage_class_name=pvc_spec.get("storageClassName"),
        volume_mode=volume_mode,
        volume_name=volume_name,
    )


def pvc_status_from_json(pvc_status: JSONPVCStatus) -> api.PersistentVolumeClaimStatus:
    phase = map_optional(api.PersistentVolumeClaimPhase, pvc_status.get("phase"))
    access_modes = map_optional(
        lambda modes: [api.AccessMode(mode) for mode in modes], pvc_status.get("accessModes")
    )
    capacity = map_optional(api.StorageRequirement.model_validate, pvc_status.get("capacity"))

    return api.PersistentVolumeClaimStatus(
        phase=phase,
        access_modes=access_modes,
        capacity=capacity,
        current_volume_attributes_class_name=pvc_status.get("currentVolumeAttributesClassName"),
    )


def persistent_volume_claim_from_json(
    persistent_volume_claim: JSONPersistentVolumeClaim,
) -> api.PersistentVolumeClaim:
    return api.PersistentVolumeClaim(
        metadata=_metadata_from_json(persistent_volume_claim["metadata"]),
        spec=pvc_spec_from_json(persistent_volume_claim["spec"]),
        status=pvc_status_from_json(persistent_volume_claim["status"]),
    )
