#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

from typing import Mapping

from kubernetes import client  # type: ignore[import]
from pydantic_factories import ModelFactory

from cmk.special_agents.utils_kubernetes.controllers import _match_controllers
from cmk.special_agents.utils_kubernetes.schemata import api

POD_UID = "pod_uid"
POD = client.V1Pod(metadata=client.V1ObjectMeta(uid=POD_UID))


class OwnerReferenceFactory(ModelFactory):
    __model__ = api.OwnerReference


def test_controller_matched_to_pod() -> None:
    owner_cronjob = OwnerReferenceFactory.build(kind="CronJob", controller=True)
    owner_job = OwnerReferenceFactory.build(kind="Job", controller=True)
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [owner_job],
        owner_job.uid: [owner_cronjob],
        owner_cronjob.uid: [],
    }
    assert _match_controllers([POD], object_to_owners) == (
        {owner_cronjob.uid: [POD_UID]},
        {
            POD_UID: [
                api.Controller(
                    type_=api.ControllerType.cronjob,
                    name=owner_cronjob.name,
                    namespace=owner_cronjob.namespace,
                )
            ]
        },
    )


def test_controller_not_added_if_not_a_controller() -> None:
    owner_cronjob = OwnerReferenceFactory.build(kind="CronJob", controller=True)
    owner_job = OwnerReferenceFactory.build(kind="Job", controller=False)
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [owner_job],
        owner_job.uid: [owner_cronjob],
        owner_cronjob.uid: [],
    }
    assert _match_controllers([POD], object_to_owners) == ({}, {})


def test_controller_not_added_if_not_a_controller_object_mapping() -> None:
    owner_cronjob = OwnerReferenceFactory.build(kind="CronJob", controller=False)
    owner_job = OwnerReferenceFactory.build(kind="Job", controller=True)
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [owner_job],
        owner_job.uid: [owner_cronjob],
        owner_cronjob.uid: [],
    }
    assert _match_controllers([POD], object_to_owners) == ({}, {})


def test_controller_not_in_object_to_owners() -> None:
    object_to_owners: Mapping[str, api.OwnerReferences] = {"somethingelse": [], POD_UID: []}
    assert _match_controllers([POD], object_to_owners) == ({}, {})


def test_pod_does_not_have_owner_ref() -> None:
    owner_cronjob = OwnerReferenceFactory.build(kind="CronJob")
    owner_job = OwnerReferenceFactory.build(kind="Job")
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [],
        owner_job.uid: [owner_cronjob],
        owner_cronjob.uid: [],
    }
    assert _match_controllers([POD], object_to_owners) == ({}, {})


def test_multiple_owners() -> None:
    owner_cronjob = OwnerReferenceFactory.build(kind="CronJob", controller=True)
    owner_job = OwnerReferenceFactory.build(kind="Job", controller=True)
    owner_deployment = OwnerReferenceFactory.build(kind="Deployment", controller=True)
    owner_replicaset = OwnerReferenceFactory.build(kind="ReplicaSet", controller=True)
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [owner_job, owner_replicaset],
        owner_job.uid: [owner_cronjob],
        owner_cronjob.uid: [],
        owner_replicaset.uid: [owner_deployment],
        owner_deployment.uid: [],
    }
    assert _match_controllers([POD], object_to_owners) == (
        {
            owner_cronjob.uid: [POD_UID],
            owner_deployment.uid: [POD_UID],
        },
        {
            POD_UID: [
                api.Controller(
                    type_=api.ControllerType.cronjob,
                    name=owner_cronjob.name,
                    namespace=owner_cronjob.namespace,
                ),
                api.Controller(
                    type_=api.ControllerType.deployment,
                    name=owner_deployment.name,
                    namespace=owner_deployment.namespace,
                ),
            ]
        },
    )
