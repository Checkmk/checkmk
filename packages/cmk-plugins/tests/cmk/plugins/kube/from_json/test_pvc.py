# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.plugins.kube.from_json.pvc import (
    JSONPersistentVolumeClaim,
    persistent_volume_claim_from_json,
)
from cmk.plugins.kube.schemata.api import (
    AccessMode,
    PersistentVolumeClaimPhase,
    PersistentVolumeMode,
    VolumeName,
)
from tests.cmk.plugins.kube.data.kube_1_34 import (
    pvc_with_volume_attributes_class_name,
    pvc_without_volume_attributes_class_name,
)


@pytest.mark.parametrize(
    "json",
    [
        pvc_with_volume_attributes_class_name.DATA,
        pvc_without_volume_attributes_class_name.DATA,
    ],
)
def test_persistent_volume_claim_from_json(json: JSONPersistentVolumeClaim) -> None:
    pvc = persistent_volume_claim_from_json(json)
    assert pvc.metadata.name == "test-pvc"
    assert pvc.spec.access_modes == [AccessMode.READ_WRITE_ONCE]
    assert pvc.spec.resources is not None
    assert pvc.spec.resources.requests is not None
    assert pvc.spec.resources.requests.storage == 1073741824
    assert pvc.spec.resources.limits is None
    assert pvc.spec.storage_class_name == "manual"
    assert pvc.spec.volume_mode == PersistentVolumeMode.FILESYSTEM
    assert pvc.spec.volume_name == VolumeName("test-local-pv")
    assert pvc.status.phase == PersistentVolumeClaimPhase.CLAIM_BOUND
    assert pvc.status.access_modes == [AccessMode.READ_WRITE_ONCE]
    assert pvc.status.capacity is not None
    assert pvc.status.capacity.storage == 1073741824


def test_persistent_volume_claim_from_json_minimal() -> None:
    # All spec/status fields are optional; ensure the None paths through
    # map_optional resolve cleanly when the K8s API omits them.
    json: JSONPersistentVolumeClaim = {
        "metadata": {
            "uid": "00000000-0000-0000-0000-000000000000",
            "name": "minimal-pvc",
            "namespace": "default",
        },
        "spec": {},
        "status": {},
    }
    pvc = persistent_volume_claim_from_json(json)
    assert pvc.metadata.name == "minimal-pvc"
    assert pvc.spec.access_modes is None
    assert pvc.spec.resources is None
    assert pvc.spec.storage_class_name is None
    assert pvc.spec.volume_mode is None
    assert pvc.spec.volume_name is None
    assert pvc.status.phase is None
    assert pvc.status.access_modes is None
    assert pvc.status.capacity is None
