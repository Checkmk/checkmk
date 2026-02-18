#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""JSON parsing for Kubernetes API objects.

This file contains helper functions to parse JSON received from the Kubernetes
API into version independent data structures defined in `schemata.api`. This
parsing is an alternate approach to the Kubernetes client. The Kubernetes
client could no longer be upgraded, because v1.23.3 would reject valid
API data, see CMK-10826.
"""

from collections.abc import Iterable, Mapping, Sequence
from typing import cast, Literal, NotRequired, TypedDict

from .schemata import api
from .schemata.api import convert_to_timestamp
from .transform_any import parse_match_labels

# StatefulSet


class JSONOwnerReference(TypedDict):
    uid: str
    controller: NotRequired[bool]
    kind: str
    name: str
    namespace: NotRequired[str]


JSONOwnerReferences = Sequence[JSONOwnerReference]


class JSONSelectorRequirement(TypedDict):
    key: str
    operator: str
    values: Sequence[str] | None


class JSONSelector(TypedDict, total=False):
    matchLabels: Mapping[str, str]
    matchExpressions: Sequence[JSONSelectorRequirement]


class JSONMetaData(TypedDict):
    uid: str
    name: str
    namespace: str
    creationTimestamp: str
    labels: NotRequired[Mapping[str, str]]
    annotations: NotRequired[Mapping[str, str]]
    ownerReferences: NotRequired[JSONOwnerReferences]


class JSONObjectWithMetadata(TypedDict):
    metadata: JSONMetaData


# == StatefulSet ==


class JSONStatefulSetRollingUpdate_(TypedDict):
    partition: int
    maxUnavailable: NotRequired[str]


class JSONStatefulSetRollingUpdate(TypedDict):
    type: Literal["RollingUpdate"]
    rollingUpdate: NotRequired[JSONStatefulSetRollingUpdate_]


class JSONStatefulSetOnDelete(TypedDict):
    type: Literal["OnDelete"]


JSONStatefulSetUpdateStrategy = JSONStatefulSetOnDelete | JSONStatefulSetRollingUpdate


class JSONStatefulSetSpec(TypedDict):
    minReadySeconds: NotRequired[int]
    replicas: int
    selector: JSONSelector
    updateStrategy: JSONStatefulSetUpdateStrategy


class JSONStatefulSet(JSONObjectWithMetadata):
    spec: JSONStatefulSetSpec
    status: object


class JSONStatefulSetList(TypedDict):
    items: Sequence[JSONStatefulSet]


# == Deployment ==


class JSONDeploymentStrategyRollingUpdate_(TypedDict):
    maxSurge: NotRequired[str | int]
    maxUnavailable: NotRequired[str | int]


class JSONDeploymentStrategyRollingUpdate(TypedDict):
    type: Literal["RollingUpdate"]
    rollingUpdate: NotRequired[JSONDeploymentStrategyRollingUpdate_]


class JSONDeploymentStrategyRecreate(TypedDict):
    type: Literal["Recreate"]


JSONDeploymentStrategy = JSONDeploymentStrategyRollingUpdate | JSONDeploymentStrategyRecreate


class JSONDeploymentSpec(TypedDict):
    minReadySeconds: NotRequired[int]
    strategy: JSONDeploymentStrategy
    selector: JSONSelector
    replicas: int


class JSONDeploymentCondition(TypedDict):
    type: str
    status: str
    lastTransitionTime: str
    reason: str
    message: str


class JSONDeploymentStatus(TypedDict):
    availableReplicas: NotRequired[int]
    unavailableReplicas: NotRequired[int]
    readyReplicas: NotRequired[int]
    replicas: NotRequired[int]
    updatedReplicas: NotRequired[int]
    terminatingReplicas: NotRequired[int]
    conditions: NotRequired[Sequence[JSONDeploymentCondition]]


class JSONDeployment(JSONObjectWithMetadata):
    spec: JSONDeploymentSpec
    status: JSONDeploymentStatus


class JSONDeploymentList(TypedDict):
    items: Sequence[JSONDeployment]


# == Node ==


class JSONNodeMetaData(TypedDict):
    name: api.NodeName
    creationTimestamp: str
    labels: NotRequired[Mapping[str, str]]
    annotations: NotRequired[Mapping[str, str]]


class JSONNode(TypedDict):
    metadata: JSONNodeMetaData
    status: object


class JSONNodeList(TypedDict):
    items: Sequence[JSONNode]


def _metadata_from_json(metadata: JSONMetaData) -> api.MetaData:
    return api.MetaData.model_validate(metadata)


def _metadata_no_namespace_from_json(metadata: JSONNodeMetaData) -> api.NodeMetaData:
    return api.NodeMetaData.model_validate(metadata)


def _parse_match_expression_from_json(
    match_expressions: Iterable[JSONSelectorRequirement] | None,
) -> api.MatchExpressions:
    return [
        api.MatchExpression(
            key=api.LabelName(expression["key"]),
            operator=cast(Literal["In", "NotIn", "Exists", "DoesNotExist"], expression["operator"]),
            values=[api.LabelValue(v) for v in expression["values"] or []],
        )
        for expression in match_expressions or []
    ]


def _selector_from_json(selector: JSONSelector) -> api.Selector:
    return api.Selector(
        match_labels=parse_match_labels(selector.get("matchLabels", {})),
        match_expressions=_parse_match_expression_from_json(selector.get("matchExpressions", [])),
    )


def _statefulset_update_strategy_from_json(
    statefulset_update_strategy: JSONStatefulSetUpdateStrategy,
) -> api.OnDelete | api.StatefulSetRollingUpdate:
    if statefulset_update_strategy["type"] == "OnDelete":
        return api.OnDelete()
    if statefulset_update_strategy["type"] == "RollingUpdate":
        if rolling_update := statefulset_update_strategy.get("rollingUpdate"):
            partition = rolling_update["partition"]
            max_unavailable = rolling_update.get("maxUnavailable")
        else:
            partition = 0
            max_unavailable = None
        return api.StatefulSetRollingUpdate(partition=partition, max_unavailable=max_unavailable)
    raise ValueError(f"Unknown strategy type: {statefulset_update_strategy['type']}")


def _statefulset_spec_from_json(spec: JSONStatefulSetSpec) -> api.StatefulSetSpec:
    return api.StatefulSetSpec(
        min_ready_seconds=spec.get("minReadySeconds", 0),
        strategy=_statefulset_update_strategy_from_json(spec["updateStrategy"]),
        selector=_selector_from_json(spec["selector"]),
        replicas=spec["replicas"],
    )


def statefulset_from_json(
    statefulset: JSONStatefulSet,
    pod_uids: Sequence[api.PodUID],
) -> api.StatefulSet:
    return api.StatefulSet(
        metadata=_metadata_from_json(statefulset["metadata"]),
        spec=_statefulset_spec_from_json(statefulset["spec"]),
        status=api.StatefulSetStatus.model_validate(statefulset["status"]),
        pods=pod_uids,
    )


def deployment_replicas(status: JSONDeploymentStatus, spec: JSONDeploymentSpec) -> api.Replicas:
    # A deployment always has at least 1 replica. It is not possible to deploy
    # a deployment that has 0 replicas. On the other hand, it is possible to have
    # 0 available/unavailable/updated/ready replicas. This is shown as 'null'
    # (i.e. None) in the source data, but the interpretation is that the number
    # of the replicas in this case is 0.
    # Under certain conditions, the status.replicas can report a 'null' value, therefore
    # the spec.replicas is taken as base value since this reflects the desired value
    return api.Replicas(
        replicas=spec["replicas"],
        available=status.get("availableReplicas", 0),
        unavailable=status.get("unavailableReplicas", 0),
        updated=status.get("updatedReplicas", 0),
        ready=status.get("readyReplicas", 0),
    )


def deployment_conditions(
    status: JSONDeploymentStatus,
) -> Mapping[str, api.DeploymentCondition]:
    return {
        condition["type"].lower(): api.DeploymentCondition(
            status=api.ConditionStatus(condition["status"]),
            last_transition_time=convert_to_timestamp(condition["lastTransitionTime"]),
            reason=condition["reason"],
            message=condition["message"],
        )
        for condition in status.get("conditions") or []
    }


def parse_deployment_spec(deployment_spec: JSONDeploymentSpec) -> api.DeploymentSpec:
    if deployment_spec["strategy"]["type"] == "Recreate":
        return api.DeploymentSpec(
            min_ready_seconds=deployment_spec.get("minReadySeconds", 0),
            strategy=api.Recreate(),
            selector=_selector_from_json(deployment_spec["selector"]),
        )
    if deployment_spec["strategy"]["type"] == "RollingUpdate":
        return api.DeploymentSpec(
            min_ready_seconds=deployment_spec.get("minReadySeconds", 0),
            strategy=api.RollingUpdate(
                max_surge=deployment_spec["strategy"]["rollingUpdate"]["maxSurge"],
                max_unavailable=deployment_spec["strategy"]["rollingUpdate"]["maxUnavailable"],
            ),
            selector=_selector_from_json(deployment_spec["selector"]),
        )
    raise ValueError(f"Unknown strategy type: {deployment_spec['strategy']['type']}")


def deployment_from_json(
    deployment: JSONDeployment, pod_uids: Sequence[api.PodUID]
) -> api.Deployment:
    return api.Deployment(
        metadata=_metadata_from_json(deployment["metadata"]),
        spec=parse_deployment_spec(deployment["spec"]),
        status=api.DeploymentStatus(
            conditions=deployment_conditions(deployment["status"]),
            replicas=deployment_replicas(deployment["status"], deployment["spec"]),
            number_terminating=deployment["status"].get("terminatingReplicas"),
        ),
        pods=pod_uids,
    )


def dependent_object_uid_from_json(
    dependent: JSONObjectWithMetadata,
) -> str:
    return dependent["metadata"]["uid"]


def dependent_object_owner_refererences_from_json(
    dependent: JSONObjectWithMetadata,
) -> api.OwnerReferences:
    return [
        api.OwnerReference(
            uid=ref["uid"],
            controller=ref.get("controller"),
            kind=ref["kind"],
            name=ref["name"],
            namespace=dependent["metadata"].get("namespace"),
        )
        for ref in dependent["metadata"].get("ownerReferences", [])
    ]


def node_list_from_json(
    node_list_raw: JSONNodeList,
    node_to_kubelet_health: Mapping[str, api.HealthZ | api.NodeConnectionError],
) -> Sequence[api.Node]:
    return [
        api.Node(
            metadata=_metadata_no_namespace_from_json(node["metadata"]),
            status=api.NodeStatus.model_validate(node["status"]),
            kubelet_health=node_to_kubelet_health[node["metadata"]["name"]],
        )
        for node in node_list_raw["items"]
    ]
