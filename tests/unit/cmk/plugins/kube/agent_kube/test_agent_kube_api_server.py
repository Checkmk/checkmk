#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.plugins.kube.controllers import (
    _find_controllers,
    CompleteControlChain,
    IncompleteControlChain,
)
from cmk.plugins.kube.schemata import api

POD_UID = api.PodUID("pod_uid")


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
    assert _find_controllers(POD_UID, object_to_owners) == CompleteControlChain(
        chain=[
            api.Controller(
                type_=owner_job.kind,
                uid=owner_job.uid,
                name=owner_job.name,
                namespace=owner_job.namespace,
            ),
            api.Controller(
                type_=owner_cronjob.kind,
                uid=owner_cronjob.uid,
                name=owner_cronjob.name,
                namespace=owner_cronjob.namespace,
            ),
        ],
    )


def test_controller_not_added_if_not_a_controller() -> None:
    owner_cronjob = OwnerReferenceFactory.build(kind="CronJob", controller=True)
    owner_job = OwnerReferenceFactory.build(kind="Job", controller=False)
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [owner_job],
        owner_job.uid: [owner_cronjob],
        owner_cronjob.uid: [],
    }
    assert _find_controllers(POD_UID, object_to_owners) == CompleteControlChain(chain=[])


def test_controller_not_added_if_not_a_controller_object_mapping() -> None:
    owner_cronjob = OwnerReferenceFactory.build(kind="CronJob", controller=False)
    owner_job = OwnerReferenceFactory.build(kind="Job", controller=True)
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [owner_job],
        owner_job.uid: [owner_cronjob],
        owner_cronjob.uid: [],
    }
    assert _find_controllers(POD_UID, object_to_owners) == CompleteControlChain(
        chain=[
            api.Controller(
                type_=owner_job.kind,
                uid=owner_job.uid,
                name=owner_job.name,
                namespace=owner_job.namespace,
            )
        ]
    )


def test_controller_not_in_object_to_owners() -> None:
    object_to_owners: Mapping[str, api.OwnerReferences] = {"somethingelse": [], POD_UID: []}
    assert _find_controllers(POD_UID, object_to_owners) == CompleteControlChain(chain=[])


def test_pod_does_not_have_owner_ref() -> None:
    owner_cronjob = OwnerReferenceFactory.build(kind="CronJob")
    owner_job = OwnerReferenceFactory.build(kind="Job")
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [],
        owner_job.uid: [owner_cronjob],
        owner_cronjob.uid: [],
    }
    assert _find_controllers(POD_UID, object_to_owners) == CompleteControlChain(chain=[])


def test_multiple_owners() -> None:
    owner_cronjob = OwnerReferenceFactory.build(kind="CronJob", controller=True)
    owner_job = OwnerReferenceFactory.build(kind="Job", controller=True)
    owner_deployment = OwnerReferenceFactory.build(kind="Deployment", controller=False)
    owner_replicaset = OwnerReferenceFactory.build(kind="ReplicaSet", controller=False)
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [owner_job, owner_replicaset],
        owner_job.uid: [owner_cronjob],
        owner_cronjob.uid: [],
        owner_replicaset.uid: [owner_deployment],
        owner_deployment.uid: [],
    }
    assert _find_controllers(POD_UID, object_to_owners) == CompleteControlChain(
        chain=[
            api.Controller(
                type_=owner_job.kind,
                uid=owner_job.uid,
                name=owner_job.name,
                namespace=owner_job.namespace,
            ),
            api.Controller(
                type_=owner_cronjob.kind,
                uid=owner_cronjob.uid,
                name=owner_cronjob.name,
                namespace=owner_cronjob.namespace,
            ),
        ]
    )


def test_unknown_owner() -> None:
    owner_unknown = OwnerReferenceFactory.build(kind="Unknown", controller=True)
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [owner_unknown],
    }
    assert _find_controllers(POD_UID, object_to_owners) == IncompleteControlChain(
        chain=[
            api.Controller(
                type_=owner_unknown.kind,
                uid=owner_unknown.uid,
                name=owner_unknown.name,
                namespace=owner_unknown.namespace,
            ),
        ]
    )
