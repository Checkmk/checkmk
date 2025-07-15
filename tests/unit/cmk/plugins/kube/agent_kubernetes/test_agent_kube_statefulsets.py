#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.kube.schemata import api
from cmk.plugins.kube.transform import parse_metadata

from tests.unit.cmk.plugins.kube.agent_kubernetes.utils import FakeResponse


class TestAPIStatefulSets:
    def test_parse_metadata(self, apps_client, dummy_host) -> None:  # type: ignore[no-untyped-def]
        statefulsets_metadata = {
            "metadata": {
                "name": "web",
                "namespace": "default",
                "uid": "29be93ae-eba8-4b2b-8eb9-2e76378b4e87",
                "resourceVersion": "54122",
                "generation": 1,
                "creationTimestamp": "2022-03-09T07:44:17Z",
                "labels": {"app": "nginx"},
                "annotations": {"foo": "bar"},
            },
        }

        statefulset = apps_client.api_client.deserialize(
            FakeResponse(statefulsets_metadata), "V1StatefulSet"
        )
        metadata = parse_metadata(statefulset.metadata)
        assert isinstance(metadata, api.MetaData)
        assert metadata.name == "web"
        assert isinstance(metadata.creation_timestamp, float)
        assert metadata.labels
        assert metadata.annotations == {"foo": "bar"}

    def test_parse_metadata_missing_annotations_and_labels(  # type: ignore[no-untyped-def]
        self, apps_client, dummy_host
    ) -> None:
        statefulsets_metadata = {
            "metadata": {
                "name": "web",
                "namespace": "default",
                "uid": "29be93ae-eba8-4b2b-8eb9-2e76378b4e87",
                "resourceVersion": "54122",
                "generation": 1,
                "creationTimestamp": "2022-03-09T07:44:17Z",
            },
        }

        statefulset = apps_client.api_client.deserialize(
            FakeResponse(statefulsets_metadata), "V1StatefulSet"
        )
        metadata = parse_metadata(statefulset.metadata)
        assert metadata.labels == {}
        assert metadata.annotations == {}

    def test_parse_status_successful_creation(self) -> None:
        statefulset_data = {
            "observedGeneration": 1,
            "replicas": 3,
            "readyReplicas": 3,
            "currentReplicas": 3,
            "updatedReplicas": 3,
            "currentRevision": "web-578cfc4b46",
            "updateRevision": "web-578cfc4b46",
            "collisionCount": 0,
            "availableReplicas": 3,
        }

        status = api.StatefulSetStatus.model_validate(statefulset_data)
        assert status.ready_replicas == 3
        assert status.updated_replicas == 3

    def test_parse_status_failed_creation(self) -> None:
        statefulset_data = {
            "observedGeneration": 1,
            "replicas": 1,
            "currentReplicas": 1,
            "updatedReplicas": 1,
            "currentRevision": "web-from-docs-86f4d798f6",
            "updateRevision": "web-from-docs-86f4d798f6",
            "collisionCount": 0,
        }

        status = api.StatefulSetStatus.model_validate(statefulset_data)
        assert status.ready_replicas == 0
        assert status.updated_replicas == 1
