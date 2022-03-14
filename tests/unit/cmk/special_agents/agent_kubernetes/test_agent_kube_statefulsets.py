import json

from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import parse_metadata


class TestAPIStatefulSets:
    def test_parse_metadata(self, apps_client, dummy_host):
        statefulsets_metadata = {
            "items": [
                {
                    "metadata": {
                        "name": "web",
                        "namespace": "default",
                        "uid": "29be93ae-eba8-4b2b-8eb9-2e76378b4e87",
                        "resourceVersion": "54122",
                        "generation": 1,
                        "creationTimestamp": "2022-03-09T07:44:17Z",
                        "labels": {"app": "nginx"},
                        "annotations": {},
                    },
                }
            ]
        }

        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/apps/v1/statefulsets",
            body=json.dumps(statefulsets_metadata),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            statefulset = list(apps_client.list_stateful_set_for_all_namespaces().items)[0]
        metadata = parse_metadata(statefulset.metadata)
        assert isinstance(metadata, api.MetaData)
        assert metadata.name == "web"
        assert isinstance(metadata.creation_timestamp, float)
        assert metadata.labels
