import json

from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import pod_conditions


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
