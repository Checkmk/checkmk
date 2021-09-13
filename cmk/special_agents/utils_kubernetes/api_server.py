from typing import Dict, Sequence

from kubernetes import client  # type: ignore[import] # pylint: disable=import-error

from cmk.special_agents.utils_kubernetes.schemas import NodeAPI, PodAPI


class CoreAPI:
    def __init__(self, api_client: client.ApiClient) -> None:
        self.connection = client.CoreV1Api(api_client)
        self._nodes: Dict[str, NodeAPI] = {}
        self._pods: Dict[str, PodAPI] = {}
        self._collect_objects()

    def nodes(self) -> Sequence[NodeAPI]:
        return tuple(self._nodes.values())

    def pods(self) -> Sequence[PodAPI]:
        return tuple(self._pods.values())

    def _collect_objects(self):
        self._collect_nodes()
        self._collect_pods()

    def _collect_pods(self):
        self._pods.update({
            pod.metadata.name: PodAPI.from_client(pod)
            for pod in self.connection.list_pod_for_all_namespaces().items
        })

    def _collect_nodes(self):
        self._nodes.update({
            node.metadata.name: NodeAPI.from_client(node)
            for node in self.connection.list_node().items
        })


class APIServer:
    @classmethod
    def from_kubernetes(cls, api_client):
        return cls(CoreAPI(api_client))

    def __init__(
        self,
        core_api: CoreAPI,
    ) -> None:
        self.core_api = core_api

    def nodes(self) -> Sequence[NodeAPI]:
        return self.core_api.nodes()

    def pods(self) -> Sequence[PodAPI]:
        return self.core_api.pods()
