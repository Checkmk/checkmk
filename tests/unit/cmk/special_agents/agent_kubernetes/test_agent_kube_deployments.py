#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Mapping

from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import deployment_conditions, parse_metadata


class TestAPIDeployments:
    def test_parse_metadata(self, apps_client, dummy_host) -> None:
        mocked_deployments = {
            "items": [
                {
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
                },
            ]
        }
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/deployments",
            body=json.dumps(mocked_deployments),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            deployment = list(apps_client.list_deployment_for_all_namespaces().items)[0]

        metadata = parse_metadata(deployment.metadata)
        assert metadata.name == "cluster-collector"
        assert metadata.namespace == "checkmk-monitoring"
        assert isinstance(metadata.creation_timestamp, float)
        assert metadata.labels == {"app": api.Label(name="app", value="cluster-collector")}
        assert metadata.annotations == {"deployment.kubernetes.io/revision": "2"}

    def test_parse_metadata_missing_annotations_and_labels(self, apps_client, dummy_host) -> None:
        mocked_deployments = {
            "items": [
                {
                    "metadata": {
                        "name": "cluster-collector",
                        "namespace": "checkmk-monitoring",
                        "uid": "debc9fe4-9e45-4688-ad04-a95604fa1f30",
                        "resourceVersion": "207264",
                        "generation": 2,
                        "creationTimestamp": "2022-03-25T13:24:42Z",
                    },
                },
            ]
        }
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/deployments",
            body=json.dumps(mocked_deployments),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            deployment = list(apps_client.list_deployment_for_all_namespaces().items)[0]

        metadata = parse_metadata(deployment.metadata)
        assert metadata.name == "cluster-collector"
        assert metadata.namespace == "checkmk-monitoring"
        assert isinstance(metadata.creation_timestamp, float)
        assert metadata.labels == {}
        assert metadata.annotations == {}

    def test_parse_conditions(self, apps_client, dummy_host) -> None:
        deployment_with_conditions = {
            "items": [
                {
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
            ]
        }

        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/deployments",
            body=json.dumps(deployment_with_conditions),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            deployment = list(apps_client.list_deployment_for_all_namespaces().items)[0]
        conditions = deployment_conditions(deployment.status)
        assert len(conditions) == 2
        assert all(
            isinstance(condition, api.DeploymentCondition) for _, condition in conditions.items()
        )
        assert all(
            condition.status == api.ConditionStatus.TRUE for _, condition in conditions.items()
        )

    def test_parse_conditions_no_conditions(self, apps_client, dummy_host) -> None:
        """Deployment with empty status.

        Sometimes a Deployment has an empty status. This occurs during start-up
        of the Minikube with the core-dns Deployment."""
        # Arrange
        deployment_with_conditions: Mapping = {
            "items": [
                {"status": {}},
            ]
        }
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/deployments",
            body=json.dumps(deployment_with_conditions),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            deployment = apps_client.list_deployment_for_all_namespaces().items[0]
        # Act
        conditions = deployment_conditions(deployment.status)
        # Assert
        assert conditions == {}
