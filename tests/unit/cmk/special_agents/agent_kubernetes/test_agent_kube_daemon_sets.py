#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import parse_daemonset_status, parse_metadata


class TestAPIDaemonSets:
    def test_parse_metadata(self, apps_client, dummy_host) -> None:
        daemon_sets_metadata = {
            "items": [
                {
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
            ]
        }

        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/daemonsets",
            body=json.dumps(daemon_sets_metadata),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            daemon_set = list(apps_client.list_daemon_set_for_all_namespaces().items)[0]
        metadata = parse_metadata(daemon_set.metadata)
        assert isinstance(metadata, api.MetaData)
        assert metadata.name == "node-collector-container-metrics"
        assert isinstance(metadata.creation_timestamp, float)
        assert metadata.labels
        assert metadata.annotations == {"deprecated.daemonset.template.generation": "1"}

    def test_parse_metadata_missing_annotations_and_labels(self, apps_client, dummy_host) -> None:
        daemon_sets_metadata = {
            "items": [
                {
                    "metadata": {
                        "name": "node-collector-container-metrics",
                        "namespace": "checkmk-monitoring",
                        "uid": "6f07cb60-26c7-41ce-afe0-48c97d15a07b",
                        "resourceVersion": "2967286",
                        "generation": 1,
                        "creationTimestamp": "2022-02-16T10:03:21Z",
                    }
                }
            ]
        }

        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/daemonsets",
            body=json.dumps(daemon_sets_metadata),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            daemon_set = list(apps_client.list_daemon_set_for_all_namespaces().items)[0]
        metadata = parse_metadata(daemon_set.metadata)
        assert metadata.labels == {}
        assert metadata.annotations == {}

    def test_parse_status_failed_creation(self, apps_client, dummy_host) -> None:
        daemon_sets_data = {
            "items": [
                {
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
            ]
        }

        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/daemonsets",
            body=json.dumps(daemon_sets_data),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            daemon_set = list(apps_client.list_daemon_set_for_all_namespaces().items)[0]
        status = parse_daemonset_status(daemon_set.status)
        assert status.number_misscheduled == 0
        assert status.number_ready == 0
        assert status.desired_number_scheduled == 2
        assert status.updated_number_scheduled == 1

    def test_parse_status_no_matching_node(self, apps_client, dummy_host) -> None:
        """

        Some DaemonSets may have no Nodes, on which they want to schedule Pods (because of their
        NodeSelector or NodeAffinity). In this case, some status fields are omitted.
        """

        daemon_sets_data = {
            "items": [
                {
                    "status": {
                        "currentNumberScheduled": 0,
                        "numberMisscheduled": 0,
                        "desiredNumberScheduled": 0,
                        "numberReady": 0,
                        "observedGeneration": 1,
                    }
                }
            ]
        }

        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/daemonsets",
            body=json.dumps(daemon_sets_data),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            daemon_set = list(apps_client.list_daemon_set_for_all_namespaces().items)[0]
        status = parse_daemonset_status(daemon_set.status)
        assert status.number_misscheduled == 0
        assert status.number_ready == 0
        assert status.desired_number_scheduled == 0
        assert status.updated_number_scheduled == 0
