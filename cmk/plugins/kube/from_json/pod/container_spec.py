# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, NotRequired, TypedDict

from ...schemata import api
from ..resources import JSONResourceRequirements


class JSONContainerSpec(TypedDict):
    name: str
    imagePullPolicy: Literal["Always", "IfNotPresent", "Never"]
    resources: NotRequired[JSONResourceRequirements]


def container_resources(container: JSONContainerSpec) -> api.ResourceRequirements:
    parsed_limits = api.ResourceRequirement()
    parsed_requests = api.ResourceRequirement()
    if resources := container.get("resources"):
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


def containers_spec(containers: Sequence[JSONContainerSpec]) -> Sequence[api.ContainerSpec]:
    return [
        api.ContainerSpec(
            name=api.ContainerName(container["name"]),
            resources=container_resources(container),
            image_pull_policy=container["imagePullPolicy"],
        )
        for container in containers
    ]
