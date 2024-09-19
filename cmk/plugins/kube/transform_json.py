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
from .transform_any import parse_match_labels

# StatefulSet


class JSONOwnerReference(TypedDict):
    uid: str
    controller: NotRequired[bool]
    kind: str
    name: str
    namespace: NotRequired[str]


JSONOwnerReferences = Sequence[JSONOwnerReference]


class JSONStatefulSetMetaData(TypedDict):
    uid: str
    name: str
    namespace: str
    creationTimestamp: str
    labels: NotRequired[Mapping[str, str]]
    annotations: NotRequired[Mapping[str, str]]
    ownerReferences: NotRequired[JSONOwnerReferences]


class RollingUpdate(TypedDict):
    partition: int
    maxUnavailable: NotRequired[str]


class JSONStatefulSetRollingUpdate(TypedDict):
    type: Literal["RollingUpdate"]
    rollingUpdate: NotRequired[RollingUpdate]


class JSONStatefulSetOnDelete(TypedDict):
    type: Literal["OnDelete"]


JSONStatefulSetUpdateStrategy = JSONStatefulSetOnDelete | JSONStatefulSetRollingUpdate


class JSONSelectorRequirement(TypedDict):
    key: str
    operator: str
    values: Sequence[str] | None


class JSONSelector(TypedDict, total=False):
    matchLabels: Mapping[str, str]
    matchExpressions: Sequence[JSONSelectorRequirement]


class JSONStatefulSetSpec(TypedDict):
    minReadySeconds: NotRequired[int]
    replicas: int
    selector: JSONSelector
    updateStrategy: JSONStatefulSetUpdateStrategy


class JSONStatefulSet(TypedDict):
    metadata: JSONStatefulSetMetaData
    spec: JSONStatefulSetSpec
    status: object


class JSONStatefulSetList(TypedDict):
    items: Sequence[JSONStatefulSet]


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


def _metadata_from_json(metadata: JSONStatefulSetMetaData) -> api.MetaData:
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


def _statefulset_from_json(
    statefulset: JSONStatefulSet,
    pod_uids: Sequence[api.PodUID],
) -> api.StatefulSet:
    return api.StatefulSet(
        metadata=_metadata_from_json(statefulset["metadata"]),
        spec=_statefulset_spec_from_json(statefulset["spec"]),
        status=api.StatefulSetStatus.model_validate(statefulset["status"]),
        pods=pod_uids,
    )


def statefulset_list_from_json(
    statefulset_list: JSONStatefulSetList,
    controller_to_pods: Mapping[str, Sequence[api.PodUID]],
) -> Sequence[api.StatefulSet]:
    return [
        _statefulset_from_json(
            statefulset, controller_to_pods.get(dependent_object_uid_from_json(statefulset), [])
        )
        for statefulset in statefulset_list["items"]
    ]


def dependent_object_uid_from_json(
    dependent: JSONStatefulSet,
) -> str:
    return dependent["metadata"]["uid"]


def dependent_object_owner_refererences_from_json(
    dependent: JSONStatefulSet,
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
