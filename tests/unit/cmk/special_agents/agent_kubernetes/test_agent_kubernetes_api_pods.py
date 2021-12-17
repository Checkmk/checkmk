import datetime
import json
from typing import Mapping, Optional, Sequence
from unittest import TestCase
from unittest.mock import Mock

import pytest
from dateutil.tz import tzutc
from kubernetes import client  # type: ignore[import] # pylint: disable=import-error
from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.agent_kube import _collect_memory_resources, Pod
from cmk.special_agents.utils_kubernetes.schemata import api, section
from cmk.special_agents.utils_kubernetes.schemata.section import ExceptionalResource
from cmk.special_agents.utils_kubernetes.transform import (
    convert_to_timestamp,
    pod_conditions,
    pod_containers,
    pod_spec,
)


class TestAPIPod:
    def test_parse_conditions(self, core_client, dummy_host):
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

    def test_parse_containers(self, core_client, dummy_host):
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
        containers = pod_containers(pod)
        assert len(containers) == 1
        assert "cadvisor" in containers
        assert containers["cadvisor"].ready is True
        assert containers["cadvisor"].state.type == "running"
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
        pod = client.V1Pod(
            status=client.V1PodStatus(
                container_statuses=None,
            )
        )

        container_info_api_list = pod_containers(pod)

        self.assertEqual(container_info_api_list, {})

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
        pod = client.V1Pod(
            status=client.V1PodStatus(
                container_statuses=[
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
                ],
            ),
        )
        self.assertEqual(
            pod_containers(pod),
            {
                "unready_container": api.ContainerInfo(
                    id=None,
                    name="unready_container",
                    image="gcr.io/kuar-demo/kuard-amd64:blue",
                    ready=False,
                    state=api.ContainerWaitingState(
                        type="waiting", reason="ContainerCreating", detail=None
                    ),
                    restart_count=0,
                )
            },
        )

    def test_pod_conditions_start_up(self) -> None:
        """
        It is possible that during startup of pods, also more complete information arises.
        """
        pod_status = api.PodStatus(
            start_time=int(
                convert_to_timestamp(datetime.datetime(2021, 11, 22, 16, 11, 38, 710257))
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
            status=pod_status,
            metadata=Mock(),
            spec=Mock(),
            containers=Mock(),
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
                    convert_to_timestamp(datetime.datetime(2021, 11, 22, 16, 11, 38, 710257))
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


def _other_requirement(requirement: str) -> str:
    return "requests" if requirement == "limits" else "limits"


def _pod_from_container_values(
    container_values: Sequence[Optional[float]],
    requirement: str,
    resource: str,
) -> Pod:
    spec = api.PodSpec(
        restart_policy="Always",
        containers=[
            api.ContainerSpec(
                resources=api.ContainerResources(
                    **{
                        requirement: api.ResourcesRequirements(**{resource: value}),
                        _other_requirement(requirement): api.ResourcesRequirements(),
                    }
                ),
                name=f"{resource}{i}",
            )
            for i, value in enumerate(container_values)
        ],
    )
    return Pod(uid=Mock(), metadata=Mock(), status=Mock(), spec=spec, containers=Mock())


_CONTAINER_VALUES: Mapping[str, Sequence[Optional[float]]] = {
    "only_zero": [0.0],
    "only_normal": [1.0],
    "all_exceptional": [None, 0.0],
    "all_values": [0.0, 1.0, None],
    "one_zero": [1.0, 0.0],
    "one_unspecified": [None, 1.0],
    "only_unspecified": [None],
}


@pytest.mark.parametrize(
    """
        requirement,
        expected_result,
        container_values_names,
    """,
    [
        (
            "requests",
            ExceptionalResource.unspecified,
            (
                "all_exceptional",
                "one_unspecified",
                "only_unspecified",
                "all_values",
            ),
        ),
        ("requests", 0.0, ("only_zero",)),
        (
            "requests",
            1.0,
            (
                "only_normal",
                "one_zero",
            ),
        ),
        (
            "limits",
            ExceptionalResource.zero,
            (
                "one_zero",
                "only_zero",
            ),
        ),
        (
            "limits",
            ExceptionalResource.unspecified,
            (
                "only_unspecified",
                "one_unspecified",
            ),
        ),
        (
            "limits",
            1.0,
            ("only_normal",),
        ),
        (
            "limits",
            ExceptionalResource.zero_unspecified,
            (
                "all_exceptional",
                "all_values",
            ),
        ),
    ],
)
def test_aggregate_via_pod(requirement, expected_result, container_values_names) -> None:
    """
    Aggregation needs to be done on the agent-side rather than the check-side, in order to
    deduplicate container metrics (a container may belong to several Kubernetes objects).

    We test the aggregation as done by the pod.
    """
    for resource in ("memory", "cpu"):
        for name in container_values_names:
            pod = _pod_from_container_values(_CONTAINER_VALUES[name], requirement, resource)
            aggregater = getattr(pod, f"{resource}_{requirement[:-1]}")
            assert aggregater() == expected_result


@pytest.mark.parametrize(
    """
        requirement,
        expected_result,
        possible_values_per_pod,
    """,
    [
        (
            "requests",
            ExceptionalResource.unspecified,
            (
                ["one_unspecified"],
                ["only_unspecified"],
                ["all_exceptional", "only_normal"],
                ["all_values", "only_normal"],
            ),
        ),
        (
            "requests",
            1.0,
            (
                ["only_normal"],
                ["one_zero"],
                ["one_zero", "only_zero"],
            ),
        ),
        (
            "limits",
            ExceptionalResource.zero,
            (
                ["only_normal", "one_zero"],
                ["one_zero"],
                ["only_zero"],
            ),
        ),
        (
            "limits",
            ExceptionalResource.unspecified,
            (
                ["one_unspecified"],
                ["only_unspecified"],
                ["one_unspecified", "only_normal"],
            ),
        ),
        (
            "limits",
            ExceptionalResource.zero_unspecified,
            (
                ["one_unspecified", "only_zero"],
                ["only_unspecified", "only_zero", "only_normal"],
                ["all_values"],
            ),
        ),
        (
            "limits",
            1.0,
            (["only_normal"],),
        ),
    ],
)
def test_collect_memory_resources(requirement, expected_result, possible_values_per_pod) -> None:
    """
    Aggregation needs to be done on the agent-side rather than the check-side, in order to
    deduplicate container metrics (a container may belong to several Kubernetes objects).

    We test the aggregation of the memory resources as done by clusters, deployments, nodes.
    """
    for values_per_pod in possible_values_per_pod:
        pod_seq = [
            _pod_from_container_values(_CONTAINER_VALUES[values], requirement, "memory")
            for values in values_per_pod
        ]
        result = getattr(_collect_memory_resources(pod_seq), requirement[:-1])
        assert expected_result == result
