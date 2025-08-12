import fastapi

from cmk.agent_receiver.relay_backend.api.routers.base_router import RELAY_ROUTER
from cmk.agent_receiver.relay_backend.api.routers.relays.handlers.register import (
    RegisterRelayHandler,
)
from cmk.relay_protocols.relays import RelayRegistrationRequest


@RELAY_ROUTER.post("/", status_code=fastapi.status.HTTP_200_OK)
async def register_relay(
    request: RelayRegistrationRequest,
) -> fastapi.Response:
    """Register a new relay entity.

    This endpoint allows relay entities to register themselves with the Agent Receiver.
    The relay provides its ID, name, certificate signing request, and auth token.

    Args:
        request: RelayRegistrationRequest containing relay registration data

    Returns:
        Success message confirming relay registration

    Note:
        - Relay ID uniqueness is controlled during registration
        - Collision with existing relay IDs is not allowed
    """
    # Business logic for relay registration intentionally not implemented
    # - Validate relay_id uniqueness
    # - Process CSR
    # - Store relay information
    # - Generate and return appropriate certificates

    # TODO: For the handler we usually use the fastapi dependency injection system. Since the handler for now does not
    #       require any dependencies, we can just instantiate it directly.
    handler = RegisterRelayHandler()
    handler.process(request.relay_id)
    return fastapi.Response(
        status_code=fastapi.status.HTTP_200_OK, content="Relay registered successfully"
    )
