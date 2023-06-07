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
class StatefulSet(PodOwner):
    metadata: api.MetaData
    spec: api.StatefulSetSpec
    status: api.StatefulSetStatus
    type_: str = "statefulset"


def replicas(statefulset: StatefulSet) -> section.StatefulSetReplicas:
    return section.StatefulSetReplicas(
        desired=statefulset.spec.replicas,
        ready=statefulset.status.ready_replicas,
        updated=statefulset.status.updated_replicas,
        available=statefulset.status.available_replicas,
    )


def info(
    statefulset: StatefulSet,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.StatefulSetInfo:
    return section.StatefulSetInfo(
        name=statefulset.metadata.name,
        namespace=statefulset.metadata.namespace,
        creation_timestamp=statefulset.metadata.creation_timestamp,
        labels=statefulset.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            statefulset.metadata.annotations, annotation_key_pattern
        ),
        selector=statefulset.spec.selector,
        containers=thin_containers(statefulset.pods),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )
