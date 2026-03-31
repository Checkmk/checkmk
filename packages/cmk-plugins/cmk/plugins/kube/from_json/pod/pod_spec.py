# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, NotRequired, TypedDict

from ...schemata import api
from ..resources import JSONResourceRequirements
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
    resources: NotRequired[JSONResourceRequirements]


def pod_resources(pod_spec: JSONPodSpec) -> api.ResourceRequirements:
    parsed_limits = api.ResourceRequirement()
    parsed_requests = api.ResourceRequirement()
    if resources := pod_spec.get("resources"):
        if limits := resources.get("limits"):
            parsed_limits = api.ResourceRequirement(
                memory=api.parse_resource_value(limits["memory"]) if "memory" in limits else None,
                cpu=api.parse_cpu_cores(limits["cpu"]) if "cpu" in limits else None,
            )
        if requests := resources.get("requests"):
            parsed_requests = api.ResourceRequirement(
                memory=api.parse_resource_value(requests["memory"])
                if "memory" in requests
                else None,
                cpu=api.parse_cpu_cores(requests["cpu"]) if "cpu" in requests else None,
            )

    return api.ResourceRequirements(
        limits=parsed_limits,
        requests=parsed_requests,
    )


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
        resources=pod_resources(spec),
    )
