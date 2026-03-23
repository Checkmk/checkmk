# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal, NotRequired, TypedDict

from ..schemata import api
from .metadata import _metadata_from_json, JSONObjectWithMetadata
from .selector import _selector_from_json, JSONSelector


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
            last_transition_time=api.convert_to_timestamp(condition["lastTransitionTime"]),
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
