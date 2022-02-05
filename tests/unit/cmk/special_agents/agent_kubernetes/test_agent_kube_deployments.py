import json

from mocket import Mocketizer
from mocket.mockhttp import Entry

from cmk.special_agents.utils_kubernetes.transform import deployment_conditions
from cmk.special_agents.utils_kubernetes.schemata import api


class TestAPIDeployments:
    def test_parse_conditions(self, apps_client, dummy_host):
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
