#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

""" JSON parsing for Kubernetes API objects.

This file contains helper functions to parse JSON received from the Kubernetes
API into version independent data structures defined in `schemata.api`. This
parsing is an alternate approach to the Kubernetes client. The Kubernetes
client could no longer be upgraded, because v1.23.3 would reject valid
API data, see CMK-10826.
"""

from typing import Literal, Mapping, Sequence, TypedDict, Union

from .schemata import api
from .transform_any import convert_to_timestamp, parse_annotations, parse_labels

# StatefulSet


class JSONOwnerReferenceMandatory(TypedDict):
    uid: str


class JSONOwnerReferenceOptional(TypedDict, total=False):
    controller: bool


class JSONOwnerReference(JSONOwnerReferenceOptional, JSONOwnerReferenceMandatory):
    pass


JSONOwnerReferences = Sequence[JSONOwnerReference]


class JSONStatefulSetMetaDataMandatory(TypedDict):
    uid: str
    name: str
    namespace: str
    creationTimestamp: str


class JSONStatefulSetMetaDataOptional(TypedDict, total=False):
    labels: Mapping[str, str]
    annotations: Mapping[str, str]
    ownerReferences: JSONOwnerReferences


class JSONStatefulSetMetaData(JSONStatefulSetMetaDataMandatory, JSONStatefulSetMetaDataOptional):
    pass


class JSONStatefulSetRollingUpdateMandatory(TypedDict):
    type: Literal["RollingUpdate"]


class JSONStatefulSetRollingUpdateOptional(TypedDict, total=False):
    rollingUpdate: Mapping[Literal["partition"], int]


class JSONStatefulSetRollingUpdate(
    JSONStatefulSetRollingUpdateMandatory, JSONStatefulSetRollingUpdateOptional
):
    pass


class JSONStatefulSetOnDelete(TypedDict):
    type: Literal["OnDelete"]


JSONStatefulSetUpdateStrategy = JSONStatefulSetOnDelete | JSONStatefulSetRollingUpdate


class JSONSelectorRequirement(TypedDict):
    key: str
    operator: str
    values: Sequence[str]


class JSONSelector(TypedDict, total=False):
    matchLabels: Mapping[str, str]
    matchExpressions: Sequence[JSONSelectorRequirement]


class JSONStatefulSetSpec(TypedDict):
    replicas: int
    selector: JSONSelector
    updateStrategy: JSONStatefulSetUpdateStrategy


class JSONStatefulSetStatusBelow23(TypedDict, total=False):
    readyReplicas: int
    updatedReplicas: int


class JSONStatefulSetStatusAt23Mandatory(TypedDict):
    availableReplicas: int


class JSONStatefulSetStatusAt23(JSONStatefulSetStatusAt23Mandatory, JSONStatefulSetStatusBelow23):
    pass


JSONStatefulSetStatus = Union[JSONStatefulSetStatusAt23, JSONStatefulSetStatusBelow23]


class JSONStatefulSet(TypedDict):
    metadata: JSONStatefulSetMetaData
    spec: JSONStatefulSetSpec
    status: JSONStatefulSetStatus


class JSONStatefulSetList(TypedDict):
    items: Sequence[JSONStatefulSet]


def _metadata_from_json(metadata: JSONStatefulSetMetaData) -> api.MetaData:
    return api.MetaData(
        name=metadata["name"],
        namespace=api.NamespaceName(metadata["namespace"]),
        creation_timestamp=convert_to_timestamp(metadata["creationTimestamp"]),
        labels=parse_labels(metadata.get("labels", {})),
        annotations=parse_annotations(metadata.get("annotations", {})),
    )


def _selector_from_json(selector: JSONSelector) -> api.Selector:
    return api.Selector(
        match_labels=selector.get("matchLabels", {}),
        match_expressions=selector.get("matchExpressions", []),
    )


def _statefulset_update_strategy_from_json(
    statefulset_update_strategy: JSONStatefulSetUpdateStrategy,
) -> Union[api.OnDelete, api.StatefulSetRollingUpdate]:
    if statefulset_update_strategy["type"] == "OnDelete":
        return api.OnDelete()
    if statefulset_update_strategy["type"] == "RollingUpdate":
        partition = (
            rolling_update["partition"]
            if (rolling_update := statefulset_update_strategy.get("rollingUpdate"))
            else 0
        )
        return api.StatefulSetRollingUpdate(partition=partition)
    raise ValueError(f"Unknown strategy type: {statefulset_update_strategy['type']}")


def _statefulset_spec_from_json(spec: JSONStatefulSetSpec) -> api.StatefulSetSpec:
    return api.StatefulSetSpec(
        strategy=_statefulset_update_strategy_from_json(spec["updateStrategy"]),
        selector=_selector_from_json(spec["selector"]),
        replicas=spec["replicas"],
    )


def _statefulset_status_from_json(status: JSONStatefulSetStatus) -> api.StatefulSetStatus:
    return api.StatefulSetStatus(
        ready_replicas=status.get("readyReplicas", 0),
        updated_replicas=status.get("updatedReplicas", 0),
    )


def _statefulset_from_json(
    statefulset: JSONStatefulSet,
    pod_uids: Sequence[api.PodUID],
) -> api.StatefulSet:
    return api.StatefulSet(
        metadata=_metadata_from_json(statefulset["metadata"]),
        spec=_statefulset_spec_from_json(statefulset["spec"]),
        status=_statefulset_status_from_json(statefulset["status"]),
        pods=pod_uids,
    )


def statefulset_list_from_json(
    statefulset_list: JSONStatefulSetList,
    controller_to_pods: Mapping[str, Sequence[api.PodUID]],
) -> Sequence[api.StatefulSet]:
    return [
        _statefulset_from_json(
            statefulset, controller_to_pods[dependent_object_uid_from_json(statefulset)]
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
        )
        for ref in dependent["metadata"].get("ownerReferences", [])
    ]
