import uuid

from fastapi.testclient import TestClient


def test_two_relays_cannot_have_the_same_id(
    site_name: str, agent_receiver_test_client: TestClient
) -> None:
    """
    Test CT-3. Description:

    POST /relays/{relay_id}
    POST /relays/{relay_id} -> 409 Conflict
    """

    relay_id = str(uuid.uuid4())

    response = agent_receiver_test_client.post(
        f"/{site_name}/agent-receiver/relays",
        json={
            "relay_id": relay_id,
            "relay_name": "Relay A",
            "csr": "CSR for Relay A",
            "auth_token": "auth-token-A",
        },
    )
    assert response.status_code == 200, f"Failed to register relay A: {response.text}"

    response_conflict = agent_receiver_test_client.post(
        f"/{site_name}/agent-receiver/relays",
        json={
            "relay_id": relay_id,
            "relay_name": "Relay A",
            "csr": "CSR for Relay A",
            "auth_token": "auth-token-A",
        },
    )
    assert response_conflict.status_code == 409, (
        f"Expected 409 Conflict for duplicate relay A registration, got: {response_conflict.text}"
    )
