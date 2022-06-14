#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import parse_metadata, parse_statefulset_status


class TestAPIStatefulSets:
    def test_parse_metadata(self, apps_client, dummy_host) -> None:
        statefulsets_metadata = {
            "items": [
                {
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
            ]
        }

        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/statefulsets",
            body=json.dumps(statefulsets_metadata),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            statefulset = list(apps_client.list_stateful_set_for_all_namespaces().items)[0]
        metadata = parse_metadata(statefulset.metadata)
        assert isinstance(metadata, api.MetaData)
        assert metadata.name == "web"
        assert isinstance(metadata.creation_timestamp, float)
        assert metadata.labels
        assert metadata.annotations == {"foo": "bar"}

    def test_parse_metadata_missing_annotations_and_labels(self, apps_client, dummy_host) -> None:
        statefulsets_metadata = {
            "items": [
                {
                    "metadata": {
                        "name": "web",
                        "namespace": "default",
                        "uid": "29be93ae-eba8-4b2b-8eb9-2e76378b4e87",
                        "resourceVersion": "54122",
                        "generation": 1,
                        "creationTimestamp": "2022-03-09T07:44:17Z",
                    },
                }
            ]
        }

        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/statefulsets",
            body=json.dumps(statefulsets_metadata),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            statefulset = list(apps_client.list_stateful_set_for_all_namespaces().items)[0]
        metadata = parse_metadata(statefulset.metadata)
        assert metadata.labels == {}
        assert metadata.annotations == {}

    def test_parse_status_successful_creation(self, apps_client, dummy_host) -> None:
        statefulsets_data = {
            "items": [
                {
                    "status": {
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
                }
            ]
        }

        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/statefulsets",
            body=json.dumps(statefulsets_data),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            statefulset = list(apps_client.list_stateful_set_for_all_namespaces().items)[0]
        status = parse_statefulset_status(statefulset.status)
        assert status.ready_replicas == 3
        assert status.updated_replicas == 3

    def test_parse_status_failed_creation(self, apps_client, dummy_host) -> None:
        statefulsets_data = {
            "items": [
                {
                    "status": {
                        "observedGeneration": 1,
                        "replicas": 1,
                        "currentReplicas": 1,
                        "updatedReplicas": 1,
                        "currentRevision": "web-from-docs-86f4d798f6",
                        "updateRevision": "web-from-docs-86f4d798f6",
                        "collisionCount": 0,
                    }
                }
            ]
        }

        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/statefulsets",
            body=json.dumps(statefulsets_data),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            statefulset = list(apps_client.list_stateful_set_for_all_namespaces().items)[0]
        status = parse_statefulset_status(statefulset.status)
        assert status.ready_replicas == 0
        assert status.updated_replicas == 1
