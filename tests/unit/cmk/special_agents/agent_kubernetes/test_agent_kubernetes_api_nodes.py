import datetime
import json

from kubernetes import client  # type: ignore[import] # pylint: disable=import-error
from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.transform import Labels, node_conditions, parse_metadata


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
            ),
            "uid": "42c82288-5524-49cb-af75-065e73fedc88",
        }
        metadata_obj = client.V1ObjectMeta(**node_raw_metadata)
        labels = Labels(labels)
        metadata = parse_metadata(metadata_obj)
        assert metadata.name == "k8"
        assert metadata.namespace is None

    def test_parse_metadata_datetime(self):
        now = datetime.datetime(2021, 10, 11, 13, 53, 10)
        node_raw_metadata = {
            "name": "unittest",
            "creation_timestamp": now,
            "uid": "f57f3e64-2a89-11ec-bb97-3f4358ab72b2",
        }
        metadata_obj = client.V1ObjectMeta(**node_raw_metadata)
        metadata = parse_metadata(metadata_obj)
        assert metadata.creation_timestamp == now.timestamp()

    def test_parse_conditions(self, core_client, dummy_host):
        node_with_conditions = {
            "items": [
                {
                    "status": {
                        "conditions": [
                            {
                                "type": "MemoryPressure",
                                "status": "False",
                            },
                            {
                                "type": "DiskPressure",
                                "status": "False",
                            },
                            {
                                "type": "PIDPressure",
                                "status": "False",
                            },
                            {
                                "type": "Ready",
                                "status": "True",
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
        conditions = node_conditions(node)
        assert conditions is not None
        assert conditions.NetworkUnavailable is None
        assert conditions.Ready is True
