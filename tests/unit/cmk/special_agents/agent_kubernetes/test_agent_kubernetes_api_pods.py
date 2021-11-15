import json

from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import pod_conditions, pod_containers


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
        assert containers[0].ready is True
        assert containers[0].state.type == "running"
        assert containers[0].image == "some_image"
        assert isinstance(containers[0].state.start_time, int)
