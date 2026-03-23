# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, NotRequired, TypedDict

from ..schemata import api
from .metadata import _metadata_from_json, JSONObjectWithMetadata
from .selector import _selector_from_json, JSONSelector


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
