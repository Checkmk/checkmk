#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

from typing import Mapping

from kubernetes import client  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.controllers import _match_controllers
from cmk.special_agents.utils_kubernetes.schemata import api

POD_UID = "pod_uid"
POD = client.V1Pod(metadata=client.V1ObjectMeta(uid=POD_UID))


def test_controller_matched_to_pod() -> None:
    job_owner_reference = {
        "cronjob": api.OwnerReference(
            uid="cronjob_uid",
            controller=True,
            kind="CronJob",
            name="mycron",
            namespace="namespace-name",
        )
    }
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [api.OwnerReference(kind="Job", name="test-job", uid="job_uid", controller=True)],
        "job_uid": [job_owner_reference["cronjob"]],
        "cronjob_uid": [],
    }
    assert _match_controllers([POD], object_to_owners) == (
        {"cronjob_uid": [POD_UID]},
        {
            POD_UID: [
                api.Controller(
                    type_=api.ControllerType.cronjob, name="mycron", namespace="namespace-name"
                )
            ]
        },
    )


def test_controller_not_added_if_not_a_controller() -> None:
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [api.OwnerReference(kind="Job", name="test-job", uid="job_uid", controller=False)],
        "job_uid": [api.OwnerReference(uid="cronjob_uid", controller=True, kind="Job", name="myj")],
        "cronjob_uid": [],
    }
    assert _match_controllers([POD], object_to_owners) == ({}, {})


def test_controller_not_added_if_not_a_controller_object_mapping() -> None:
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [api.OwnerReference(kind="Job", name="test-job", uid="job_uid", controller=True)],
        "job_uid": [
            api.OwnerReference(uid="cronjob_uid", controller=False, kind="CronJob", name="mycron")
        ],
        "cronjob_uid": [],
    }
    assert _match_controllers([POD], object_to_owners) == ({}, {})


def test_controller_not_in_object_to_owners() -> None:
    object_to_owners: Mapping[str, api.OwnerReferences] = {"somethingelse": [], POD_UID: []}
    assert _match_controllers([POD], object_to_owners) == ({}, {})


def test_pod_does_not_have_owner_ref() -> None:
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [],
        "job_uid": [
            api.OwnerReference(uid="cronjob_uid", controller=True, kind="CronJob", name="mycron")
        ],
        "cronjob_uid": [],
    }
    assert _match_controllers([POD], object_to_owners) == ({}, {})


def test_multiple_owners() -> None:
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        POD_UID: [
            api.OwnerReference(
                kind="Job",
                name="test-job",
                uid="job_uid",
                controller=True,
            ),
            api.OwnerReference(
                kind="ReplicaSet",
                name="replicas",
                uid="replica_uid",
                controller=True,
            ),
        ],
        "job_uid": [
            api.OwnerReference(
                uid="cronjob_uid",
                controller=True,
                kind="CronJob",
                name="mycron",
                namespace="ns-name",
            )
        ],
        "cronjob_uid": [],
        "replica_uid": [
            api.OwnerReference(
                uid="deployment_uid",
                controller=True,
                kind="Deployment",
                name="myd",
                namespace="ns-name",
            )
        ],
        "deployment_uid": [],
    }
    assert _match_controllers([POD], object_to_owners) == (
        {
            "cronjob_uid": [POD_UID],
            "deployment_uid": [POD_UID],
        },
        {
            POD_UID: [
                api.Controller(
                    type_=api.ControllerType.cronjob, name="mycron", namespace="ns-name"
                ),
                api.Controller(
                    type_=api.ControllerType.deployment, name="myd", namespace="ns-name"
                ),
            ]
        },
    )
