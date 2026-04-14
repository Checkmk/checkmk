# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.unit.cmk.plugins.kube.data.kube_1_34 import pod_missing_creation_timestamp

from cmk.plugins.kube.from_json.pod.pod import pod_from_client
from cmk.plugins.kube.schemata.api import (
    ContainerRunningState,
    Phase,
    PodUID,
)


def test_pod_from_client() -> None:
    pod = pod_from_client(pod_missing_creation_timestamp.DATA, controllers=[])  # type: ignore[arg-type]

    assert pod.uid == PodUID("d9a48207-cf39-4e72-b6b5-4d355d0a9491")
    assert pod.metadata.name == "checkmk-cluster-collector-84bf9d765d-lqlrf"
    assert pod.metadata.namespace == "checkmk-monitoring"
    assert pod.metadata.creation_timestamp is None
    assert pod.controllers == []

    assert pod.status.phase == Phase.RUNNING
    assert pod.status.qos_class == "burstable"

    assert pod.spec.restart_policy == "Always"
    assert pod.spec.node == "kind-worker"
    assert len(pod.spec.containers) == 1
    assert pod.spec.containers[0].name == "cluster-collector"

    assert "cluster-collector" in pod.containers
    status = pod.containers["cluster-collector"]
    assert isinstance(status.state, ContainerRunningState)
    assert status.ready is True

    assert pod.init_containers == {}

    assert pod.spec.volumes is not None
    vol_names = [v.name for v in pod.spec.volumes]
    assert "mypvc" in vol_names
    pvc_vol = next(v for v in pod.spec.volumes if v.name == "mypvc")
    assert pvc_vol.persistent_volume_claim is not None
    assert pvc_vol.persistent_volume_claim.claim_name == "test-pvc"
