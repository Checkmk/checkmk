#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from kubernetes import client  # type: ignore[import-untyped]

from tests.unit.cmk.plugins.kube.agent_kubernetes.utils import FakeResponse

from cmk.plugins.kube.schemata import api
from cmk.plugins.kube.transform import deployment_conditions, parse_metadata


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
        assert metadata.annotations == {"deployment.kubernetes.io/revision": "2"}

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

    def test_parse_conditions(self, apps_client: client.AppsV1Api, dummy_host: str) -> None:
        deployment_with_conditions = {
            "status": {
                "conditions": [
                    {
                        "type": "Available",
                        "status": "True",
                        "lastUpdateTime": "2021-12-06T14:49:09Z",
                        "lastTransitionTime": "2021-12-06T14:49:09Z",
                        "reason": "MinimumReplicasAvailable",
                        "message": "Deployment has minimum availability.",
                    },
                    {
                        "type": "Progressing",
                        "status": "True",
                        "lastUpdateTime": "2021-12-06T14:49:09Z",
                        "lastTransitionTime": "2021-12-06T14:49:06Z",
                        "reason": "NewReplicaSetAvailable",
                        "message": "ReplicaSet has successfully progressed.",
                    },
                ]
            }
        }

        deployment = apps_client.api_client.deserialize(
            FakeResponse(deployment_with_conditions), "V1Deployment"
        )
        conditions = deployment_conditions(deployment.status)
        assert len(conditions) == 2
        assert all(
            isinstance(condition, api.DeploymentCondition) for _, condition in conditions.items()
        )
        assert all(
            condition.status == api.ConditionStatus.TRUE for _, condition in conditions.items()
        )

    def test_parse_conditions_no_conditions(
        self, apps_client: client.AppsV1Api, dummy_host: str
    ) -> None:
        """Deployment with empty status.

        Sometimes a Deployment has an empty status. This occurs during start-up
        of the Minikube with the core-dns Deployment."""
        # Arrange
        deployment_with_conditions: dict[str, dict] = {"status": {}}

        deployment = apps_client.api_client.deserialize(
            FakeResponse(deployment_with_conditions), "V1Node"
        )
        # Act
        conditions = deployment_conditions(deployment.status)
        # Assert
        assert conditions == {}
