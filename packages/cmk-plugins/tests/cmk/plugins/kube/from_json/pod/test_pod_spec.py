# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="typeddict-item"

from cmk.plugins.kube.from_json.pod.pod_spec import pod_spec
from cmk.plugins.kube.schemata.api import ContainerName, NodeName, VolumeName


def test_minimal_spec() -> None:
    result = pod_spec(
        {
            "restartPolicy": "Always",
            "containers": [{"name": "web", "imagePullPolicy": "Always"}],
        }
    )
    assert result.restart_policy == "Always"
    assert len(result.containers) == 1
    assert result.containers[0].name == ContainerName("web")
    assert result.init_containers == []
    assert result.node is None
    assert result.host_network is None
    assert result.dns_policy is None
    assert result.priority_class_name is None
    assert result.active_deadline_seconds is None
    assert result.volumes is None


def test_full_spec() -> None:
    result = pod_spec(
        {
            "nodeName": "worker-1",
            "hostNetwork": False,
            "dnsPolicy": "ClusterFirst",
            "restartPolicy": "Never",
            "containers": [{"name": "main", "imagePullPolicy": "IfNotPresent"}],
            "initContainers": [{"name": "init", "imagePullPolicy": "Always"}],
            "priorityClassName": "high-priority",
            "activeDeadlineSeconds": 300,
            "volumes": [
                {"name": "data", "persistentVolumeClaim": {"claimName": "my-pvc"}},
            ],
        }
    )
    assert result.node == NodeName("worker-1")
    assert result.host_network is False
    assert result.dns_policy == "ClusterFirst"
    assert result.restart_policy == "Never"
    assert len(result.containers) == 1
    assert len(result.init_containers) == 1
    assert result.init_containers[0].name == ContainerName("init")
    assert result.priority_class_name == "high-priority"
    assert result.active_deadline_seconds == 300
    assert result.volumes is not None
    assert len(result.volumes) == 1
    assert result.volumes[0].name == VolumeName("data")
