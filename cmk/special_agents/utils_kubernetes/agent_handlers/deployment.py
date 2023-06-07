#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.special_agents.utils_kubernetes.agent_handlers.common import (
    AnnotationOption,
    Deployment,
    filter_annotations_by_key_pattern,
    thin_containers,
)
from cmk.special_agents.utils_kubernetes.schemata import api, section

# TODO: addition of test framework for output sections


def replicas(deployment: Deployment) -> section.DeploymentReplicas:
    return section.DeploymentReplicas(
        available=deployment.status.replicas.available,
        desired=deployment.status.replicas.replicas,
        ready=deployment.status.replicas.ready,
        updated=deployment.status.replicas.updated,
    )


def info(
    deployment: Deployment,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.DeploymentInfo:
    return section.DeploymentInfo(
        name=deployment.metadata.name,
        namespace=deployment.metadata.namespace,
        creation_timestamp=deployment.metadata.creation_timestamp,
        labels=deployment.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            deployment.metadata.annotations, annotation_key_pattern
        ),
        selector=deployment.spec.selector,
        containers=thin_containers(deployment.pods),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


def conditions(
    deployment_status: api.DeploymentStatus,
) -> section.DeploymentConditions | None:
    if not deployment_status.conditions:
        return None
    return section.DeploymentConditions(**deployment_status.conditions)
