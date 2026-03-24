# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, NotRequired, TypedDict

from ...schemata import api
from .container_spec import containers_spec, JSONContainerSpec
from .volume import JSONPodVolume, parse_pod_volumes


class JSONPodSpec(TypedDict):
    nodeName: NotRequired[api.NodeName]
    hostNetwork: NotRequired[bool]
    dnsPolicy: NotRequired[str]
    restartPolicy: Literal["Always", "OnFailure", "Never"]
    containers: Sequence[JSONContainerSpec]
    initContainers: NotRequired[Sequence[JSONContainerSpec]]
    priorityClassName: NotRequired[str]
    activeDeadlineSeconds: NotRequired[int]
    volumes: NotRequired[Sequence[JSONPodVolume]]


def pod_spec(spec: JSONPodSpec) -> api.PodSpec:
    return api.PodSpec(
        node=spec.get("nodeName"),
        host_network=spec.get("hostNetwork"),
        dns_policy=spec.get("dnsPolicy"),
        restart_policy=spec["restartPolicy"],
        containers=containers_spec(spec["containers"]),
        init_containers=containers_spec(spec.get("initContainers", [])),
        priority_class_name=spec.get("priorityClassName"),
        active_deadline_seconds=spec.get("activeDeadlineSeconds"),
        volumes=parse_pod_volumes(volumes) if (volumes := spec.get("volumes")) else None,
    )
