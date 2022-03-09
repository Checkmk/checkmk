import json

from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import parse_metadata


class TestAPIDaemonSets:
    def test_parse_metadata(self, apps_client, dummy_host):
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
                        "annotations": {"deprecated.daemonset.template.generation": "1"},
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
