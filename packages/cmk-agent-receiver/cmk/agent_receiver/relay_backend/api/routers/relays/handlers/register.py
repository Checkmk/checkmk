import dataclasses
from uuid import UUID

from cmk.relay_protocols.tasks import TaskResponse

# TODO: Temporal in memory storage
# TODO: We should have some internal datamodel instead of using the interface ones
RELAY_REGISTRY: dict[UUID, list[TaskResponse]] = {}


@dataclasses.dataclass
class RegisterRelayHandler:
    def process(self, relay_id: UUID) -> None:
        self.__add_registry(relay_id)

    def __add_registry(self, relay_id: UUID) -> None:
        RELAY_REGISTRY[relay_id] = []
