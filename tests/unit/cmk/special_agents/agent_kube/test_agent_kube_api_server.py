#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

from typing import Mapping

from kubernetes import client  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.api_server import _match_controllers
from cmk.special_agents.utils_kubernetes.schemata import api


def test_controller_matched_to_pod() -> None:
    pod_owner_references = {
        "job": client.V1OwnerReference(
            api_version="v1", kind="Job", name="test-job", uid="job_uid", controller=True
        )
    }
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name="test-pod",
            uid="pod",
            owner_references=[pod_owner_references["job"]],
        )
    )
    job_owner_reference = {
        "cronjob": api.OwnerReference(
            uid="cronjob_uid", controller=True, kind="CronJob", name="mycron"
        )
    }
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        "job_uid": [job_owner_reference["cronjob"]],
        "cronjob_uid": [],
    }
    assert _match_controllers([pod], object_to_owners) == (
        {"cronjob_uid": ["pod"]},
        {"pod": [api.Controller(type_=api.ControllerType.cronjob, name="mycron")]},
    )


def test_controller_not_added_if_not_a_controller() -> None:
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name="test-pod",
            uid="pod",
            owner_references=[
                client.V1OwnerReference(
                    api_version="v1", kind="Job", name="test-job", uid="job_uid", controller=False
                )
            ],
        )
    )
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        "job_uid": [api.OwnerReference(uid="cronjob_uid", controller=True, kind="Job", name="myj")],
        "cronjob_uid": [],
    }
    assert _match_controllers([pod], object_to_owners) == ({}, {})


def test_controller_not_added_if_not_a_controller_object_mapping() -> None:
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name="test-pod",
            uid="pod",
            owner_references=[
                client.V1OwnerReference(
                    api_version="v1", kind="Job", name="test-job", uid="job_uid", controller=True
                )
            ],
        )
    )
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        "job_uid": [
            api.OwnerReference(uid="cronjob_uid", controller=False, kind="CronJob", name="mycron")
        ],
        "cronjob_uid": [],
    }
    assert _match_controllers([pod], object_to_owners) == ({}, {})


def test_controller_not_in_object_to_owners() -> None:
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name="test-pod",
            uid="pod",
            owner_references=[
                client.V1OwnerReference(
                    api_version="v1", kind="Job", name="test-job", uid="job_uid", controller=True
                )
            ],
        )
    )
    object_to_owners: Mapping[str, api.OwnerReferences] = {"somethingelse": []}
    assert _match_controllers([pod], object_to_owners) == ({}, {})


def test_pod_does_not_have_owner_ref() -> None:
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(name="test-pod", uid="pod", owner_references=None)
    )
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        "job_uid": [
            api.OwnerReference(uid="cronjob_uid", controller=True, kind="CronJob", name="mycron")
        ],
        "cronjob_uid": [],
    }
    assert _match_controllers([pod], object_to_owners) == ({}, {})


def test_multiple_owners() -> None:
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name="test-pod",
            uid="pod",
            owner_references=[
                client.V1OwnerReference(
                    api_version="v1", kind="Job", name="test-job", uid="job_uid", controller=True
                ),
                client.V1OwnerReference(
                    api_version="v1",
                    kind="ReplicaSet",
                    name="replicas",
                    uid="replica_uid",
                    controller=True,
                ),
            ],
        )
    )
    object_to_owners: Mapping[str, api.OwnerReferences] = {
        "job_uid": [
            api.OwnerReference(uid="cronjob_uid", controller=True, kind="CronJob", name="mycron")
        ],
        "cronjob_uid": [],
        "replica_uid": [
            api.OwnerReference(uid="deployment_uid", controller=True, kind="Deployment", name="myd")
        ],
        "deployment_uid": [],
    }
    assert _match_controllers([pod], object_to_owners) == (
        {
            "cronjob_uid": ["pod"],
            "deployment_uid": ["pod"],
        },
        {
            "pod": [
                api.Controller(type_=api.ControllerType.cronjob, name="mycron"),
                api.Controller(type_=api.ControllerType.deployment, name="myd"),
            ]
        },
    )
