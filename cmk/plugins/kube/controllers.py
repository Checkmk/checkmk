#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from kubernetes.client import (  # type: ignore[attr-defined]
    # https://github.com/kubernetes-client/python/issues/2033
    V1Pod,
)

from cmk.plugins.kube.schemata import api


@dataclass(frozen=True)
class CompleteControlChain:
    # A sequence of controllers, e.g. deployment -> replica set. For two adjacent elements, the first
    # one controls the second one. The final element controls the pod.
    chain: Sequence[api.Controller]


@dataclass(frozen=True)
class IncompleteControlChain:
    # Not all Owners could be determined based on the API data. This can have
    # several reasons. E.g., the controller is a CustomResourceDefinition; or
    # the user has specified the UID of an object, which does not exist.
    chain: Sequence[api.Controller]


def _find_controller(owner_references: api.OwnerReferences) -> api.OwnerReference | None:
    # There is only ever one controller, Checkmk ignores non-controlling owners.
    return next((o for o in owner_references if o.controller), None)


def _find_controllers(
    pod_uid: api.PodUID, object_to_owners: Mapping[str, api.OwnerReferences]
) -> CompleteControlChain | IncompleteControlChain:
    """Match Pod to ControlChain.

    Kubernetes only provides the information which controller is directly
    controlling the Pod. For instance, if we have a ControlChain of the form
    DataBase > Deployment > ReplicaSet > Pod, then the Pod only knows about the
    ReplicaSet. In order to obtain the whole chain, we need the API data of the
    ReplicaSet and the Deployment, since each of them know about their
    controller, and thus give us one piece of the ControlChain. This why this
    function is combining data from muliple different queries to the API
    Server, aka object_to_owners.
    Note, that since DataBase is a CustomResourceDefinition Checkmk does not
    collect any API data on this resource. Therefore, we can't lookup any
    OwnerReferences of DataBase. Thus, the ControlChain ends.

    >>> owner_database = api.OwnerReference(uid='3', kind="Database", controller=True, name='', namespace='')
    >>> owner_deployment = api.OwnerReference(uid='2', kind="Deployment", controller=True, name='', namespace='')
    >>> owner_replicaset = api.OwnerReference(uid='1', kind="ReplicaSet", controller=True, name='', namespace='')
    >>> object_to_owners = {
    ...     "0": [owner_replicaset],
    ...     owner_replicaset.uid: [owner_deployment],
    ...     owner_deployment.uid: [owner_database],
    ... }
    >>> _find_controllers("0", object_to_owners)
    IncompleteControlChain(chain=[Controller(type_='ReplicaSet', uid='1', name='', namespace=''), Controller(type_='Deployment', uid='2', name='', namespace=''), Controller(type_='Database', uid='3', name='', namespace='')])
    """

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
            return IncompleteControlChain(chain=chain)
        controller = _find_controller(owners_of_controller)
    return CompleteControlChain(chain=chain)


def _find_control_chains(
    pod_uids: Iterable[api.PodUID], object_to_owners: Mapping[str, api.OwnerReferences]
) -> Mapping[api.PodUID, Sequence[api.Controller]]:
    return {pod_uid: _find_controllers(pod_uid, object_to_owners).chain for pod_uid in pod_uids}


# TODO Needs an integration test
def _match_controllers(
    pod_to_controllers: Mapping[api.PodUID, Sequence[api.Controller]],
) -> Mapping[str, Sequence[api.PodUID]]:
    """Matches controllers to the pods they control."""
    controller_to_pods: dict[str, list[api.PodUID]] = {}
    for pod_uid, chain in pod_to_controllers.items():
        for controller in chain:
            controller_to_pods.setdefault(controller.uid, []).append(pod_uid)

    return controller_to_pods


def map_controllers(
    raw_pods: Sequence[V1Pod],
    object_to_owners: Mapping[str, api.OwnerReferences],
) -> tuple[Mapping[str, Sequence[api.PodUID]], Mapping[api.PodUID, Sequence[api.Controller]]]:
    pod_to_controllers = _find_control_chains(
        pod_uids=(pod.metadata.uid for pod in raw_pods),
        object_to_owners=object_to_owners,
    )
    return _match_controllers(pod_to_controllers), pod_to_controllers


def map_controllers_top_to_down(
    object_to_owners: Mapping[str, api.OwnerReferences],
) -> Mapping[str, Sequence[str]]:
    """Creates a mapping where the key is the controller and the value a sequence of controlled
    objects
    """
    top_down_references: dict[str, list[str]] = {}
    for object_uid, owner_references in object_to_owners.items():
        for owner_reference in owner_references:
            top_down_references.setdefault(owner_reference.uid, []).append(object_uid)
    return top_down_references
