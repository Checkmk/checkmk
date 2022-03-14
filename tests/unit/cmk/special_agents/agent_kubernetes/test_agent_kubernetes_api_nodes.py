import datetime
import json

from kubernetes import client  # type: ignore[import] # pylint: disable=import-error
from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import node_conditions, node_info, parse_metadata


class TestAPINode:
    def test_parse_metadata(self):
        labels = {
            "beta.kubernetes.io/arch": "amd64",
            "beta.kubernetes.io/os": "linux",
            "kubernetes.io/arch": "amd64",
            "kubernetes.io/hostname": "k8",
            "kubernetes.io/os": "linux",
            "node-role.kubernetes.io/master": "",
        }

        node_raw_metadata = {
            "name": "k8",
            "creation_timestamp": datetime.datetime.strptime(
                "2021-05-04T09:01:13Z", "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=datetime.timezone.utc),
            "uid": "42c82288-5524-49cb-af75-065e73fedc88",
            "labels": labels,
        }
        metadata_obj = client.V1ObjectMeta(**node_raw_metadata)
        metadata = parse_metadata(metadata_obj)
        assert metadata.name == "k8"
        assert metadata.namespace is None

    def test_parse_metadata_datetime(self):
        now = datetime.datetime(2021, 10, 11, 13, 53, 10, tzinfo=datetime.timezone.utc)
        node_raw_metadata = {
            "name": "unittest",
            "creation_timestamp": now,
            "uid": "f57f3e64-2a89-11ec-bb97-3f4358ab72b2",
        }
        metadata_obj = client.V1ObjectMeta(**node_raw_metadata)
        metadata = parse_metadata(metadata_obj)
        assert metadata.creation_timestamp == now.timestamp()

    def test_parse_node_info(self, dummy_host, core_client):
        node_list_with_info = {
            "items": [
                {
                    "status": {
                        "nodeInfo": {
                            "machineID": "abd0bd9c2f234af099e849787da63620",
                            "systemUUID": "e2902c84-10c9-4d81-b52b-85a27d62b7ca",
                            "bootID": "04bae495-8ea7-4230-9bf0-9ce841201c0c",
                            "kernelVersion": "5.4.0-88-generic",
                            "osImage": "Ubuntu 20.04.3 LTS",
                            "containerRuntimeVersion": "docker://20.10.7",
                            "kubeletVersion": "v1.21.7",
                            "kubeProxyVersion": "v1.21.7",
                            "operatingSystem": "linux",
                            "architecture": "amd64",
                        },
                    },
                }
            ]
        }
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/api/v1/nodes",
            body=json.dumps(node_list_with_info),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            node = list(core_client.list_node().items)[0]
        parsed_node_info = node_info(node)
        assert isinstance(parsed_node_info, api.NodeInfo)
        assert parsed_node_info.kernel_version == "5.4.0-88-generic"
        assert parsed_node_info.os_image == "Ubuntu 20.04.3 LTS"

    def test_parse_conditions(self, core_client, dummy_host):
        node_with_conditions = {
            "items": [
                {
                    "status": {
                        "conditions": [
                            {
                                "lastHeartbeatTime": "2019-09-20T19:32:50Z",
                                "lastTransitionTime": "2019-07-09T16:17:29Z",
                                "message": "kubelet has no disk pressure",
                                "reason": "KubeletHasNoDiskPressure",
                                "status": "False",
                                "type": "DiskPressure",
                            },
                            {
                                "lastHeartbeatTime": "2019-09-20T19:32:50Z",
                                "lastTransitionTime": "2019-07-09T16:17:29Z",
                                "message": "kubelet has sufficient memory available",
                                "reason": "KubeletHasSufficientMemory",
                                "status": "False",
                                "type": "MemoryPressure",
                            },
                            {
                                "lastHeartbeatTime": "2019-07-09T16:17:47Z",
                                "lastTransitionTime": "2019-07-09T16:17:47Z",
                                "message": "RouteController created a route",
                                "reason": "RouteCreated",
                                "status": "False",
                                "type": "NetworkUnavailable",
                            },
                            {
                                "lastHeartbeatTime": "2019-09-20T19:32:50Z",
                                "lastTransitionTime": "2019-07-09T16:17:29Z",
                                "message": "kubelet has sufficient PID available",
                                "reason": "KubeletHasSufficientPID",
                                "status": "False",
                                "type": "PIDPressure",
                            },
                            {
                                "lastHeartbeatTime": "2019-09-20T19:32:50Z",
                                "lastTransitionTime": "2019-07-09T16:17:49Z",
                                "message": "kubelet is posting ready status. AppArmor enabled",
                                "reason": "KubeletReady",
                                "status": "True",
                                "type": "Ready",
                            },
                        ],
                    },
                },
            ],
        }
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/api/v1/nodes",
            body=json.dumps(node_with_conditions),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            node = list(core_client.list_node().items)[0]
        conditions = node_conditions(node.status)
        assert conditions is not None
        assert len(conditions) == 5
        assert any(c.type_ == "DiskPressure" for c in conditions)
        assert list(c.status for c in conditions if c.type_ == "Ready") == [
            api.NodeConditionStatus.TRUE
        ]

    def test_parse_conditions_no_status(self, core_client, dummy_host):
        node_with_conditions = {"items": [{"status": {}}]}  # type: ignore
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/api/v1/nodes",
            body=json.dumps(node_with_conditions),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            node = list(core_client.list_node().items)[0]
        assert node_conditions(node.status) is None

    def test_parse_conditions_no_conditions(self, core_client, dummy_host):
        node_with_conditions = {"items": [{"status": {"conditions": []}}]}  # type: ignore
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/api/v1/nodes",
            body=json.dumps(node_with_conditions),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            node = list(core_client.list_node().items)[0]
        assert node_conditions(node.status) is None
