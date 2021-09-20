import datetime
import json

import pytest
from kubernetes import client
from kubernetes.client import ApiClient
from mocket import Mocketizer
from mocket.mockhttp import Entry

from cmk.special_agents.utils_kubernetes.schemas import (
    Labels,
    node_conditions,
    node_labels,
    parse_metadata,
)


def kubernetes_api_client():
    config = client.Configuration()
    config.host = "http://dummy"
    config.api_key_prefix["authorization"] = "Bearer"
    config.api_key["authorization"] = "dummy"
    config.verify_ssl = False
    return ApiClient(config)


class TestAPINode:
    @pytest.fixture
    def core_client(self):
        return client.CoreV1Api(kubernetes_api_client())

    @pytest.fixture
    def dummy_host(self):
        return kubernetes_api_client().configuration.host

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
            "creation_timestamp": datetime.datetime.strptime("2021-05-04T09:01:13Z", "%Y-%m-%dT%H:%M:%SZ"),
            "uid": "42c82288-5524-49cb-af75-065e73fedc88",
        }
        metadata_obj = client.V1ObjectMeta(**node_raw_metadata)
        metadata = parse_metadata(metadata_obj, node_labels(Labels(labels)))
        assert metadata.name == "k8"
        assert metadata.namespace is None
        assert metadata.labels["cmk/kubernetes"] == "yes"

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
        assert conditions.NetworkUnavailable is None
        assert conditions.Ready is True
