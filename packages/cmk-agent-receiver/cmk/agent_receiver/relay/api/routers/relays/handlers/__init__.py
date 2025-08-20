from cmk.agent_receiver.relay.api.routers.relays.handlers.register_relay import (
    RegisterRelayHandler,
    RelayAlreadyRegisteredError,
)

__all__ = ["RegisterRelayHandler", "RelayAlreadyRegisteredError"]
