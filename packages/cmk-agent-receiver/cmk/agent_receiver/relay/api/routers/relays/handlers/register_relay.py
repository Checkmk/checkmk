import dataclasses

from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


class RelayAlreadyRegisteredError(Exception):
    """Exception raised when a relay is already registered."""


@dataclasses.dataclass
class RegisterRelayHandler:
    relays_repository: RelaysRepository

    def process(self, relay_id: str) -> None:
        self._add_registry(relay_id)

    def _add_registry(self, relay_id: str) -> None:
        if self.relays_repository.has_relay(relay_id):
            raise RelayAlreadyRegisteredError(f"Relay ID {relay_id} is already registered.")

        self.relays_repository.add_relay(relay_id)
