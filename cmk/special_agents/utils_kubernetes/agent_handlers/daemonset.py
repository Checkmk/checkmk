#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from dataclasses import dataclass

from cmk.special_agents.utils_kubernetes.agent_handlers.common import (
    AnnotationOption,
    filter_annotations_by_key_pattern,
    PodOwner,
    thin_containers,
)
from cmk.special_agents.utils_kubernetes.schemata import api, section


@dataclass(frozen=True)
class DaemonSet(PodOwner):
    metadata: api.MetaData
    spec: api.DaemonSetSpec
    status: api.DaemonSetStatus
    type_: str = "daemonset"


def replicas(
    daemonset: DaemonSet,
) -> section.DaemonSetReplicas:
    return section.DaemonSetReplicas(
        available=daemonset.status.number_available,
        desired=daemonset.status.desired_number_scheduled,
        updated=daemonset.status.updated_number_scheduled,
        misscheduled=daemonset.status.number_misscheduled,
        ready=daemonset.status.number_ready,
    )


def info(
    daemonset: DaemonSet,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.DaemonSetInfo:
    return section.DaemonSetInfo(
        name=daemonset.metadata.name,
        namespace=daemonset.metadata.namespace,
        creation_timestamp=daemonset.metadata.creation_timestamp,
        labels=daemonset.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            daemonset.metadata.annotations, annotation_key_pattern
        ),
        selector=daemonset.spec.selector,
        containers=thin_containers(daemonset.pods),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )
