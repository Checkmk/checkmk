#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from kubernetes import client  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import (
    dependent_object_owner_refererences_from_client,
)


def _create_api_controller(name: str, namespace: str | None, kind: str) -> api.Controller:
    return api.Controller(
        name=name,
        namespace=namespace,
        type_=api.ControllerType.from_str(kind.lower()),
    )


# TODO Needs an integration test
def _match_controllers(
    pods: Iterable[client.V1Pod], object_to_owners: Mapping[str, api.OwnerReferences]
) -> Tuple[Mapping[str, Sequence[api.PodUID]], Mapping[api.PodUID, Sequence[api.Controller]]]:
    """Matches controllers to the pods they control

    >>> pod = client.V1Pod(metadata=client.V1ObjectMeta(name="test-pod", uid="pod", owner_references=[client.V1OwnerReference(api_version="v1", kind="Job", name="test-job", uid="job", controller=True)]))
    >>> object_to_owners = {"job": [api.OwnerReference(uid='cronjob', controller=True, kind="CronJob", name="mycron", namespace='namespace_name')], "cronjob": []}
    >>> _match_controllers([pod], object_to_owners)
    ({'cronjob': ['pod']}, {'pod': [Controller(type_=<ControllerType.cronjob: 'cronjob'>, name='mycron', namespace='namespace_name')]})

    """
    # owner_reference approach is taken from these two links:
    # https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/
    # https://github.com/kubernetes-client/python/issues/946
    # We have tested the solution in the github issue. It does not work, but was good
    # enough as a prototype.

    def recursive_toplevel_owner_lookup(
        owner_references: api.OwnerReferences,
    ) -> Iterable[api.OwnerReference]:
        for owner in owner_references:
            if not owner.controller:
                continue
            if (parent := object_to_owners.get(owner.uid)) is None:
                continue
            if len(parent) == 0:
                # If an owner does not have any parent owners, then
                # the owner is the top-level-owner
                yield owner
                continue
            yield from recursive_toplevel_owner_lookup(parent)

    controller_to_pods: Dict[str, List[api.PodUID]] = {}
    pod_to_controllers: Dict[api.PodUID, List[api.Controller]] = {}
    for pod in pods:
        pod_uid = api.PodUID(pod.metadata.uid)
        for owner in recursive_toplevel_owner_lookup(
            list(dependent_object_owner_refererences_from_client(pod))
        ):
            controller_to_pods.setdefault(owner.uid, []).append(pod_uid)
            pod_to_controllers.setdefault(pod_uid, []).append(
                _create_api_controller(
                    owner.name,
                    owner.namespace,
                    owner.kind,
                )
            )

    return controller_to_pods, pod_to_controllers


def map_controllers(
    raw_pods: Sequence[client.V1Pod],
    object_to_owners: Mapping[str, api.OwnerReferences],
) -> Tuple[Mapping[str, Sequence[api.PodUID]], Mapping[api.PodUID, Sequence[api.Controller]]]:
    return _match_controllers(
        pods=raw_pods,
        object_to_owners=object_to_owners,
    )


def map_controllers_top_to_down(
    object_to_owners: Mapping[str, api.OwnerReferences]
) -> Mapping[str, Sequence[str]]:
    """Creates a mapping where the key is the controller and the value a sequence of controlled
    objects
    """
    top_down_references: Dict[str, List[str]] = {}
    for object_uid, owner_references in object_to_owners.items():
        for owner_reference in owner_references:
            top_down_references.setdefault(owner_reference.uid, []).append(object_uid)
    return top_down_references
