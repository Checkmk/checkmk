import json

import pytest
from kubernetes import client
from kubernetes.client import ApiClient
from mocket import Mocketizer
from mocket.mockhttp import Entry

from cmk.special_agents.utils_kubernetes.schemas import (
    parse_metadata,
    node_labels,
    Labels,
    node_conditions,
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
            "creation_timestamp": "2021-05-04T09:01:13Z",
            "uid": "42c82288-5524-49cb-af75-065e73fedc88",
        }
        metadata_obj = client.V1ObjectMeta(**node_raw_metadata)
        metadata = parse_metadata(metadata_obj, node_labels(Labels(labels)))
        assert metadata.name == "k8"
        assert metadata.namespace is None
        assert metadata.labels["cmk/kubernetes"] == "yes"

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
