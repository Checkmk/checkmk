#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from kubernetes import client  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api


@dataclass(frozen=True)
class CompleteControlChain:
    # A sequence of controllers, e.g. deployment -> replica set. For two adjacent elements, the first
    # one controls the second one. The final element controls the pod.
    chain: Sequence[api.Controller]


@dataclass(frozen=True)
class InCompleteControlChain:
    # Not all Owners could be determined based on the API data. This can have
    # several reasons. E.g., the controller is a CustomResourceDefinition; or
    # the user has specified the UID of an object, which does not exist.
    chain: Sequence[api.Controller]


def _find_controller(owner_references: api.OwnerReferences) -> api.OwnerReference | None:
    # There is only ever one controller, Checkmk ignores non-controlling owners.
    return next((o for o in owner_references if o.controller), None)


def _find_controllers(
    pod_uid: api.PodUID, object_to_owners: Mapping[str, api.OwnerReferences]
) -> CompleteControlChain | InCompleteControlChain:
    # owner_reference approach is taken from these two links:
    # https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/
    # https://github.com/kubernetes-client/python/issues/946
    # We have tested the solution in the github issue. It does not work, but was good
    # enough as a prototype.
    chain = []
    controller = _find_controller(object_to_owners[pod_uid])
    while controller is not None:
        chain.append(
            api.Controller(
                uid=controller.uid,
                name=controller.name,
                namespace=controller.namespace,
                type_=controller.kind,
            )
        )
        if (owners_of_controller := object_to_owners.get(controller.uid)) is None:
            # A controller exists, but it was not available from the API data we have.
            # Typically, this happens if we handle CustomResourceDefinitions.
            return InCompleteControlChain(chain=chain)
        controller = _find_controller(owners_of_controller)
    return CompleteControlChain(chain=chain)


# TODO Needs an integration test
def _match_controllers(
    pods: Iterable[client.V1Pod], object_to_owners: Mapping[str, api.OwnerReferences]
) -> Tuple[Mapping[str, Sequence[api.PodUID]], Mapping[api.PodUID, Sequence[api.Controller]]]:
    """Matches controllers to the pods they control."""
    controller_to_pods: Dict[str, List[api.PodUID]] = {}
    pod_to_controllers: Dict[api.PodUID, Sequence[api.Controller]] = {}

    for pod in pods:
        pod_uid = api.PodUID(pod.metadata.uid)
        chain = _find_controllers(pod_uid, object_to_owners)
        pod_to_controllers[pod_uid] = chain.chain
        for controller in chain.chain:
            controller_to_pods.setdefault(controller.uid, []).append(pod_uid)

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
