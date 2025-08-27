import httpx
from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import TaskType


class RelayProxy:
    """Proxy for /relay routes that builds URLs with the site_name."""

    def __init__(self, client: TestClient, site_name: str) -> None:
        self.client = client
        self.site_name = site_name

    def register_relay(self, relay_id: str) -> httpx.Response:
        return self.client.post(
            f"/{self.site_name}/agent-receiver/relays",
            json={
                "relay_id": relay_id,
                "relay_name": "Relay A",  # TODO: Remove still unused create relay fields
                "csr": "CSR for Relay A",
                "auth_token": "auth-token-A",
            },
        )

    def unregister_relay(self, relay_id: str) -> httpx.Response:
        return self.client.delete(f"/{self.site_name}/agent-receiver/relays/{relay_id}")

    def push_task(
        self,
        relay_id: str,
        task_type: TaskType,
        task_payload: str,
    ) -> httpx.Response:
        return self.client.post(
            f"/{self.site_name}/agent-receiver/relays/{relay_id}/tasks",
            json={
                "type": task_type,
                "payload": task_payload,
            },
        )
