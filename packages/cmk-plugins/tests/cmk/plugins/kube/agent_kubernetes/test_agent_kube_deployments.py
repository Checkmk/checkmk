#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="name-defined"


from kubernetes import client

from cmk.plugins.kube.schemata import api
from cmk.plugins.kube.transform import parse_metadata
from cmk.plugins.kube.transform_json import deployment_conditions, JSONDeploymentStatus
from tests.cmk.plugins.kube.agent_kubernetes.utils import FakeResponse


class TestAPIDeployments:
    def test_parse_metadata(self, apps_client: client.AppsV1Api, dummy_host: str) -> None:
        mocked_deployments = {
            "metadata": {
                "name": "cluster-collector",
                "namespace": "checkmk-monitoring",
                "uid": "debc9fe4-9e45-4688-ad04-a95604fa1f30",
                "resourceVersion": "207264",
                "generation": 2,
                "creationTimestamp": "2022-03-25T13:24:42Z",
                "labels": {"app": "cluster-collector"},
                "annotations": {
                    "deployment.kubernetes.io/revision": "2",
                    "seccomp.security.alpha.kubernetes.io/pod": "runtime/default",
                },
            },
        }
        deployment = apps_client.api_client.deserialize(
            FakeResponse(mocked_deployments),
            "V1Deployment",
        )

        metadata = parse_metadata(deployment.metadata)
        assert metadata.name == "cluster-collector"
        assert metadata.namespace == "checkmk-monitoring"
        assert isinstance(metadata.creation_timestamp, float)
        assert metadata.labels == {
            "app": api.Label(name=api.LabelName("app"), value=api.LabelValue("cluster-collector"))
        }
        assert metadata.annotations == {
            "deployment.kubernetes.io/revision": "2",
            "seccomp.security.alpha.kubernetes.io/pod": "runtime/default",
        }

    def test_parse_metadata_missing_annotations_and_labels(
        self, apps_client: client.AppsV1Api, dummy_host: str
    ) -> None:
        mocked_deployments = {
            "metadata": {
                "name": "cluster-collector",
                "namespace": "checkmk-monitoring",
                "uid": "debc9fe4-9e45-4688-ad04-a95604fa1f30",
                "resourceVersion": "207264",
                "generation": 2,
                "creationTimestamp": "2022-03-25T13:24:42Z",
            },
        }
        deployment = apps_client.api_client.deserialize(
            FakeResponse(mocked_deployments),
            "V1Deployment",
        )

        metadata = parse_metadata(deployment.metadata)
        assert metadata.name == "cluster-collector"
        assert metadata.namespace == "checkmk-monitoring"
        assert isinstance(metadata.creation_timestamp, float)
        assert metadata.labels == {}
        assert metadata.annotations == {}

    def test_parse_conditions(self) -> None:
        status: JSONDeploymentStatus = {
            "conditions": [
                {
                    "type": "Available",
                    "status": "True",
                    "lastTransitionTime": "2021-12-06T14:49:09Z",
                    "reason": "MinimumReplicasAvailable",
                    "message": "Deployment has minimum availability.",
                },
                {
                    "type": "Progressing",
                    "status": "True",
                    "lastTransitionTime": "2021-12-06T14:49:06Z",
                    "reason": "NewReplicaSetAvailable",
                    "message": "ReplicaSet has successfully progressed.",
                },
            ]
        }

        conditions = deployment_conditions(status)
        assert len(conditions) == 2
        assert all(
            isinstance(condition, api.DeploymentCondition) for _, condition in conditions.items()
        )
        assert all(
            condition.status == api.ConditionStatus.TRUE for _, condition in conditions.items()
        )

    def test_parse_conditions_no_conditions(self) -> None:
        """Deployment with empty status.

        Sometimes a Deployment has an empty status. This occurs during start-up
        of the Minikube with the core-dns Deployment."""
        status: JSONDeploymentStatus = {}
        conditions = deployment_conditions(status)
        assert conditions == {}
