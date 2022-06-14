#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
from unittest import TestCase
from unittest.mock import Mock

from dateutil.tz import tzutc
from kubernetes import client  # type: ignore[import]
from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.agent_kube import Pod
from cmk.special_agents.utils_kubernetes.schemata import api, section
from cmk.special_agents.utils_kubernetes.transform import (
    convert_to_timestamp,
    parse_metadata,
    pod_conditions,
    pod_containers,
    pod_spec,
    pod_status,
)


class TestAPIPod:
    def test_parse_metadata(self, core_client, dummy_host) -> None:
        mocked_pods = {
            "kind": "PodList",
            "apiVersion": "v1",
            "metadata": {"selfLink": "/api/v1/pods", "resourceVersion": "6605101"},
            "items": [
                {
                    "metadata": {
                        "name": "cluster-collector-595b64557d-x9t5q",
                        "generateName": "cluster-collector-595b64557d-",
                        "namespace": "checkmk-monitoring",
                        "uid": "b1c113f5-ee08-44c2-8438-a83ca240e04a",
                        "resourceVersion": "221646",
                        "creationTimestamp": "2022-03-28T09:19:41Z",
                        "labels": {"app": "cluster-collector"},
                        "annotations": {"foo": "case"},
                        "ownerReferences": [
                            {
                                "apiVersion": "apps/v1",
                                "kind": "ReplicaSet",
                                "name": "cluster-collector-595b64557d",
                                "uid": "547e9da2-cbfa-4116-9cb6-67487b11a786",
                                "controller": "true",
                                "blockOwnerDeletion": "true",
                            }
                        ],
                    },
                },
            ],
        }
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/api/v1/pods",
            body=json.dumps(mocked_pods),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            pod = list(core_client.list_pod_for_all_namespaces().items)[0]

        metadata = parse_metadata(pod.metadata, model=api.PodMetaData)
        assert metadata.name == "cluster-collector-595b64557d-x9t5q"
        assert metadata.namespace == "checkmk-monitoring"
        assert isinstance(metadata.creation_timestamp, float)
        assert metadata.labels == {"app": api.Label(name="app", value="cluster-collector")}
        assert metadata.annotations == {"foo": "case"}

    def test_parse_metadata_missing_annotations_and_labels(self, core_client, dummy_host) -> None:
        mocked_pods = {
            "kind": "PodList",
            "apiVersion": "v1",
            "metadata": {"selfLink": "/api/v1/pods", "resourceVersion": "6605101"},
            "items": [
                {
                    "metadata": {
                        "name": "cluster-collector-595b64557d-x9t5q",
                        "generateName": "cluster-collector-595b64557d-",
                        "namespace": "checkmk-monitoring",
                        "uid": "b1c113f5-ee08-44c2-8438-a83ca240e04a",
                        "resourceVersion": "221646",
                        "creationTimestamp": "2022-03-28T09:19:41Z",
                        "ownerReferences": [
                            {
                                "apiVersion": "apps/v1",
                                "kind": "ReplicaSet",
                                "name": "cluster-collector-595b64557d",
                                "uid": "547e9da2-cbfa-4116-9cb6-67487b11a786",
                                "controller": "true",
                                "blockOwnerDeletion": "true",
                            }
                        ],
                    },
                },
            ],
        }
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/api/v1/pods",
            body=json.dumps(mocked_pods),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            pod = list(core_client.list_pod_for_all_namespaces().items)[0]

        metadata = parse_metadata(pod.metadata, model=api.PodMetaData)
        assert metadata.labels == {}
        assert metadata.annotations == {}

    def test_parse_conditions(self, core_client, dummy_host) -> None:
        node_with_conditions = {
            "items": [
                {
                    "status": {
                        "conditions": [
                            {
                                "type": "Ready",
                                "status": "False",
                                "reason": None,
                                "message": None,
                                "lastTransitionTime": "2021-10-08T07:39:10Z",
                            },
                        ],
                    },
                },
            ],
        }
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/api/v1/pods",
            body=json.dumps(node_with_conditions),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            pod = list(core_client.list_pod_for_all_namespaces().items)[0]
        condition = pod_conditions(pod.status.conditions)[0]
        assert condition.detail is None
        assert condition.status is False
        assert condition.detail is None
        assert condition.type == api.ConditionType.READY

    def test_parse_containers(self, core_client, dummy_host) -> None:
        mocked_pods = {
            "kind": "PodList",
            "apiVersion": "v1",
            "metadata": {"selfLink": "/api/v1/pods", "resourceVersion": "6605101"},
            "items": [
                {
                    "status": {
                        "containerStatuses": [
                            {
                                "name": "cadvisor",
                                "state": {"running": {"startedAt": "2021-10-08T07:39:10Z"}},
                                "lastState": {},
                                "ready": True,
                                "restartCount": 0,
                                "image": "some_image",
                                "imageID": "some_irrelevant_id",
                                "containerID": "some_container_id",
                                "started": True,
                            }
                        ],
                    },
                }
            ],
        }
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/api/v1/pods",
            body=json.dumps(mocked_pods),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            pod = list(core_client.list_pod_for_all_namespaces().items)[0]
        containers = pod_containers(pod.status.container_statuses)
        assert len(containers) == 1
        assert "cadvisor" in containers
        assert containers["cadvisor"].ready is True
        assert containers["cadvisor"].state.type == api.ContainerStateType.running
        assert containers["cadvisor"].image == "some_image"
        assert isinstance(containers["cadvisor"].state, api.ContainerRunningState)
        assert isinstance(containers["cadvisor"].state.start_time, int)


class TestPodWithNoNode(TestCase):
    """If the cluster does not have any allocatable pods remaining, special client objects arise.
    For instance, these pods do not have a dedicated node.
    Below, there is one test for each affected function.
    """

    def test_parse_pod_spec_pod_without_node(self) -> None:
        pod = client.V1Pod(
            spec=client.V1PodSpec(
                host_network=None,
                node_name=None,
                containers=[
                    client.V1Container(
                        name="non_scheduled_container",
                        image_pull_policy="Always",
                    ),
                ],
                restart_policy="Always",
            ),
            status=client.V1PodStatus(
                host_ip=None,
                pod_ip=None,
                qos_class="BestEffort",
            ),
        )
        pod_spec_api = pod_spec(pod)

        assert pod_spec_api.node is None

    def test_pod_containers_pod_without_node(self) -> None:
        """both initContainerStatuses and containerStatuses will be None, if a pod could not be
        scheduled. In this case, the containers and init_containers of the api.Pod is empty"""
        self.assertEqual(pod_containers(None), {})

    def test_pod_conditions_pod_without_node(self) -> None:
        last_transition_time = datetime.datetime(2021, 10, 29, 9, 5, 52, tzinfo=tzutc())
        pod_condition_list = [
            client.V1PodCondition(
                last_probe_time=None,
                last_transition_time=last_transition_time,
                message="0/1 nodes are available: 1 Too many pods.",
                reason="Unschedulable",
                status="False",
                type="PodScheduled",
            )
        ]
        self.assertEqual(
            pod_conditions(pod_condition_list),
            [
                api.PodCondition(
                    status=False,
                    type=api.ConditionType.PODSCHEDULED,
                    custom_type=None,
                    reason="Unschedulable",
                    detail="0/1 nodes are available: 1 Too many pods.",
                    last_transition_time=convert_to_timestamp(last_transition_time),
                )
            ],
        )


class TestPodStartUp(TestCase):
    """During startup of a large number of pods, special pod conditions may arise, where most of the
    information is missing. Depending on timing, we obtain different client objects from the
    kubernetes api.
    """

    def test_pod_containers_start_up(self) -> None:
        """
        In this specific instance all of the fields expect for the scheduled field are missing.
        """
        container_statuses = [
            client.V1ContainerStatus(
                name="unready_container",
                ready=False,
                restart_count=0,
                container_id=None,
                image="gcr.io/kuar-demo/kuard-amd64:blue",
                image_id="",
                state=client.V1ContainerState(
                    running=None,
                    terminated=None,
                    waiting=client.V1ContainerStateWaiting(
                        message=None, reason="ContainerCreating"
                    ),
                ),
            )
        ]
        self.assertEqual(
            pod_containers(container_statuses),
            {
                "unready_container": api.ContainerStatus(
                    id=None,
                    name="unready_container",
                    image="gcr.io/kuar-demo/kuard-amd64:blue",
                    image_id="",
                    ready=False,
                    state=api.ContainerWaitingState(reason="ContainerCreating", detail=None),
                    restart_count=0,
                )
            },
        )

    def test_pod_conditions_start_up(self) -> None:
        """
        It is possible that during startup of pods, also more complete information arises.
        """
        api_pod_status = api.PodStatus(
            start_time=int(
                convert_to_timestamp(
                    datetime.datetime(
                        2021, 11, 22, 16, 11, 38, 710257, tzinfo=datetime.timezone.utc
                    )
                )
            ),
            conditions=[
                api.PodCondition(
                    status=True,
                    type=api.ConditionType.INITIALIZED,
                    custom_type=None,
                    reason=None,
                    detail=None,
                ),
                api.PodCondition(
                    status=False,
                    type=api.ConditionType.READY,
                    custom_type=None,
                    reason="ContainersNotReady",
                    detail="containers with unready status: [unready_container]",
                ),
                api.PodCondition(
                    status=False,
                    type=api.ConditionType.CONTAINERSREADY,
                    custom_type=None,
                    reason="ContainersNotReady",
                    detail="containers with unready status: [unready_container]",
                ),
                api.PodCondition(
                    status=True,
                    type=api.ConditionType.PODSCHEDULED,
                    custom_type=None,
                    reason=None,
                    detail=None,
                ),
            ],
            phase=api.Phase.PENDING,
            qos_class="burstable",
        )
        pod = Pod(
            uid=Mock(),
            status=api_pod_status,
            metadata=Mock(),
            spec=Mock(),
            containers=Mock(),
            init_containers=Mock(),
        )
        self.assertEqual(
            pod.conditions(),
            section.PodConditions(
                initialized=section.PodCondition(status=True, reason=None, detail=None),
                scheduled=section.PodCondition(status=True, reason=None, detail=None),
                containersready=section.PodCondition(
                    status=False,
                    reason="ContainersNotReady",
                    detail="containers with unready status: [unready_container]",
                ),
                ready=section.PodCondition(
                    status=False,
                    reason="ContainersNotReady",
                    detail="containers with unready status: [unready_container]",
                ),
            ),
        )

    def test_pod_conditions_start_up_missing_fields(self) -> None:
        """
        In this specific instance all of the fields except for the scheduled field are missing.
        """
        pod = Pod(
            uid=Mock(),
            status=api.PodStatus(
                start_time=int(
                    convert_to_timestamp(
                        datetime.datetime(
                            2021, 11, 22, 16, 11, 38, 710257, tzinfo=datetime.timezone.utc
                        )
                    )
                ),
                conditions=[
                    api.PodCondition(
                        status=True,
                        type=api.ConditionType.PODSCHEDULED,
                        custom_type=None,
                        reason=None,
                        detail=None,
                    )
                ],
                phase=api.Phase.PENDING,
                qos_class="burstable",
            ),
            metadata=Mock(),
            spec=Mock(),
            containers=Mock(),
            init_containers=Mock(),
        )

        self.assertEqual(
            pod.conditions(),
            section.PodConditions(
                initialized=None,
                scheduled=section.PodCondition(status=True, reason=None, detail=None),
                containersready=None,
                ready=None,
            ),
        )


def test_pod_status_evicted_pod() -> None:
    client_pod_status = client.V1PodStatus(
        conditions=None,
        container_statuses=None,
        ephemeral_container_statuses=None,
        host_ip=None,
        init_container_statuses=None,
        message="The node was low on resource: ephemeral-storage. Container "
        "grafana-sc-dashboard was using 4864Ki, which exceeds its request "
        "of 0. Container grafana was using 2112Ki, which exceeds its "
        "request of 0. Container grafana-sc-datasources was using 1280Ki, "
        "which exceeds its request of 0. ",
        nominated_node_name=None,
        phase="Failed",
        pod_i_ps=None,
        pod_ip=None,
        qos_class=None,
        reason="Evicted",
        start_time=datetime.datetime(2022, 5, 23, 5, 43, 57, tzinfo=tzutc()),
    )
    client_pod = client.V1Pod(status=client_pod_status)
    assert pod_status(client_pod) == api.PodStatus(
        conditions=None,
        phase=api.Phase.FAILED,
        start_time=api.Timestamp(1653284637.0),
        host_ip=None,
        pod_ip=None,
        qos_class=None,
    )
