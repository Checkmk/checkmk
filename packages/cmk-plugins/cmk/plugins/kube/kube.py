#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable, Mapping, Sequence
from typing import Literal, TypeVar

from cmk.agent_based.v2 import CheckResult, HostLabel, HostLabelGenerator
from cmk.plugins.kube.schemata.api import (
    ContainerRunningState,
    ContainerStatus,
    ContainerTerminatedState,
    ContainerWaitingState,
    Labels,
    NodeConditionStatus,
)
from cmk.plugins.kube.schemata.section import (
    BasePodLifeCycle,
    FilteredAnnotations,
    PodLifeCycle,
    Section,
)

COLLECTOR_SERVICE_NAME = "Cluster collector"


# TODO: CMK-10380 (the change will incompatible)
def kube_labels_to_cmk_labels(labels: Labels) -> HostLabelGenerator:
    """Convert Kubernetes Labels to HostLabels.

    Key-value pairs of Kubernetes labels are valid checkmk labels (see
    `LabelName` and `LabelValue`).

    However, directly yielding `HostLabel(label.name, label.value)` is
    problematic. This is because a user can add labels to their Kubernetes
    objects, which overwrite existing Checkmk labels. For instance, the label
    `cmk/os_name=` would overwrite the cmk label `cmk/os_name:linux`. To
    circumvent this problem, we prepend every label key with
    'cmk/kubernetes/label/'.

    """
    for label in labels.values():
        yield HostLabel(f"cmk/kubernetes/label/{label.name}", str(label.value) or "true")


# TODO: CMK-10380 (the change will incompatible)
def kube_annotations_to_cmk_labels(annotations: FilteredAnnotations) -> HostLabelGenerator:
    """Convert Kubernetes Annotations to HostLabels.

    Kubernetes annotations are not valid Checkmk labels, but agent_kube makes
    sure that annotations only arrive here, if we want to yield it as a
    HostLabel, e.g. a restricted set of characters.

    Directly yielding `HostLabel(annotation.name, annotation.value)` is
    problematic. This is because a user can add annotations to their Kubernetes
    objects, which overwrite existing Checkmk labels. For instance, the
    annotation `cmk/os_name=` would overwrite the cmk label
    `cmk/os_name:linux`. To circumvent this problem, we prepend every
    annotation key with 'cmk/kubernetes/annotation/'.

    >>> annotations = {
    ... 'k8s.io/app': 'nginx',
    ... 'infra': 'yes',
    ... 'empty': '',
    ... }
    >>> list(kube_annotations_to_cmk_labels(annotations))
    [HostLabel('cmk/kubernetes/annotation/k8s.io/app', 'nginx'), HostLabel('cmk/kubernetes/annotation/infra', 'yes'), HostLabel('cmk/kubernetes/annotation/empty', 'true')]
    """
    for name, value in annotations.items():
        yield HostLabel(f"cmk/kubernetes/annotation/{name}", value or "true")


class KubernetesError(Exception):
    pass


def condition_short_description(name: str, status: NodeConditionStatus | bool) -> str:
    if isinstance(status, NodeConditionStatus):
        return f"{name.upper()}: {status.value}"
    return f"{name.upper()}: {status}"


def condition_detailed_description(
    name: str,
    status: NodeConditionStatus | bool,
    reason: str | None,
    message: str | None,
) -> str:
    """Format the condition for Result summary or details

    Examples:
        >>> condition_detailed_description("Ready", NodeConditionStatus.FALSE, "Waiting", "ContainerCreating")
        'READY: False (Waiting: ContainerCreating)'

    """
    return f"{condition_short_description(name, status)} ({reason}: {message})"


VSResultAge = tuple[Literal["levels"], tuple[int, int]] | Literal["no_levels"]


def get_age_levels_for(params: Mapping[str, VSResultAge], key: str) -> tuple[int, int] | None:
    """Get the levels for the given key from the params

    Examples:
        >>> params = dict(
        ...     initialized="no_levels",
        ...     scheduled=("levels", (89, 179)),
        ...     containersready="no_levels",
        ...     ready=("levels", (359, 719)),
        ... )
        >>> get_age_levels_for(params, "initialized")
        >>> get_age_levels_for(params, "scheduled")
        (89, 179)
        >>> get_age_levels_for(params, "containersready")
        >>> get_age_levels_for(params, "ready")
        (359, 719)
        >>> get_age_levels_for({}, "ready")
    """
    levels = params.get(key, "no_levels")
    if levels == "no_levels":
        return None
    return levels[1]


def erroneous_or_incomplete_containers(
    containers: Sequence[ContainerStatus],
) -> Sequence[ContainerStatus]:
    return [
        container
        for container in containers
        if not isinstance(container.state, ContainerRunningState)
        and not (
            isinstance(container.state, ContainerTerminatedState) and container.state.exit_code == 0
        )
    ]


T = TypeVar("T", bound=Section)


def check_with_time(
    check_function: Callable[[float, T], CheckResult],
) -> Callable[[T], CheckResult]:
    def check_function_with_time(section: T) -> CheckResult:
        yield from check_function(time.time(), section)

    return check_function_with_time


def pod_status_message(
    pod_containers: Sequence[ContainerStatus],
    pod_init_containers: Sequence[ContainerStatus],
    section_kube_pod_lifecycle: PodLifeCycle | BasePodLifeCycle,
) -> str:
    if init_container_message := _pod_container_message(pod_init_containers):
        return f"Init:{init_container_message}"
    if container_message := _pod_container_message(pod_containers):
        return container_message
    return section_kube_pod_lifecycle.phase.title()


def _pod_container_message(pod_containers: Sequence[ContainerStatus]) -> str | None:
    containers = erroneous_or_incomplete_containers(pod_containers)
    for container in containers:
        if (
            isinstance(container.state, ContainerWaitingState)
            and container.state.reason != "ContainerCreating"
        ):
            return container.state.reason
    for container in containers:
        if (
            isinstance(container.state, ContainerTerminatedState)
            and container.state.reason is not None
        ):
            return container.state.reason
    return None
