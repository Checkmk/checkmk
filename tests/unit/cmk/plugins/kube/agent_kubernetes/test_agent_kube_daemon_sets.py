#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from kubernetes import client  # type: ignore[import-untyped]

from tests.unit.cmk.plugins.kube.agent_kubernetes.utils import FakeResponse

from cmk.plugins.kube.schemata import api
from cmk.plugins.kube.transform import parse_daemonset_status, parse_metadata


class TestAPIDaemonSets:
    def test_parse_metadata(self, apps_client: client.AppsV1Api, dummy_host: str) -> None:
        daemon_sets_metadata = {
            "metadata": {
                "name": "node-collector-container-metrics",
                "namespace": "checkmk-monitoring",
                "uid": "6f07cb60-26c7-41ce-afe0-48c97d15a07b",
                "resourceVersion": "2967286",
                "generation": 1,
                "creationTimestamp": "2022-02-16T10:03:21Z",
                "labels": {"app": "node-collector-container-metrics"},
                "annotations": {
                    "deprecated.daemonset.template.generation": "1",
                    "seccomp.security.alpha.kubernetes.io/pod": "runtime/default",
                },
            }
        }

        daemon_set = apps_client.api_client.deserialize(
            FakeResponse(daemon_sets_metadata),
            "V1DaemonSet",
        )
        metadata = parse_metadata(daemon_set.metadata)
        assert isinstance(metadata, api.MetaData)
        assert metadata.name == "node-collector-container-metrics"
        assert isinstance(metadata.creation_timestamp, float)
        assert metadata.labels
        assert metadata.annotations == {"deprecated.daemonset.template.generation": "1"}

    def test_parse_metadata_missing_annotations_and_labels(
        self, apps_client: client.AppsV1Api, dummy_host: str
    ) -> None:
        daemon_sets_metadata = {
            "metadata": {
                "name": "node-collector-container-metrics",
                "namespace": "checkmk-monitoring",
                "uid": "6f07cb60-26c7-41ce-afe0-48c97d15a07b",
                "resourceVersion": "2967286",
                "generation": 1,
                "creationTimestamp": "2022-02-16T10:03:21Z",
            }
        }

        daemon_set = apps_client.api_client.deserialize(
            FakeResponse(daemon_sets_metadata),
            "V1DaemonSet",
        )
        metadata = parse_metadata(daemon_set.metadata)
        assert metadata.labels == {}
        assert metadata.annotations == {}

    def test_parse_status_failed_creation(
        self, apps_client: client.AppsV1Api, dummy_host: str
    ) -> None:
        daemon_sets_data = {
            "status": {
                "currentNumberScheduled": 1,
                "numberMisscheduled": 0,
                "desiredNumberScheduled": 2,
                "numberReady": 0,
                "observedGeneration": 1,
                "updatedNumberScheduled": 1,
                "numberUnavailable": 1,
            }
        }

        daemon_set = apps_client.api_client.deserialize(
            FakeResponse(daemon_sets_data), "V1DaemonSet"
        )
        status = parse_daemonset_status(daemon_set.status)
        assert status.number_misscheduled == 0
        assert status.number_ready == 0
        assert status.desired_number_scheduled == 2
        assert status.updated_number_scheduled == 1

    def test_parse_status_no_matching_node(
        self, apps_client: client.AppsV1Api, dummy_host: str
    ) -> None:
        """

        Some DaemonSets may have no Nodes, on which they want to schedule Pods (because of their
        NodeSelector or NodeAffinity). In this case, some status fields are omitted.
        """

        daemon_sets_data = {
            "status": {
                "currentNumberScheduled": 0,
                "numberMisscheduled": 0,
                "desiredNumberScheduled": 0,
                "numberReady": 0,
                "observedGeneration": 1,
            }
        }

        daemon_set = apps_client.api_client.deserialize(
            FakeResponse(daemon_sets_data), "V1DaemonSet"
        )
        status = parse_daemonset_status(daemon_set.status)
        assert status.number_misscheduled == 0
        assert status.number_ready == 0
        assert status.desired_number_scheduled == 0
        assert status.updated_number_scheduled == 0
