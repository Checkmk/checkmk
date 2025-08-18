import dataclasses
import uuid

from cmk.relay_protocols.tasks import TaskResponse

# Persistence layer is not thread safe yet.
# Note: Since we are using async endpoints in the agent-receiver
# the executions are added as a coroutine to the main async event loop.
# The persistence layer is for now an in memory dict so we won't need
# to make this thread-safe as this should not be accessed by multiple threads
# concurrently.
GLOBAL_RELAYS: dict[uuid.UUID, list[TaskResponse]] = {}


@dataclasses.dataclass
class RelaysRepository:
    def add_relay(self, relay_id: uuid.UUID) -> None:
        GLOBAL_RELAYS[relay_id] = []

    def list_relays(self) -> list[uuid.UUID]:
        return list(GLOBAL_RELAYS.keys())

    def get_relay_tasks(self, relay_id: uuid.UUID) -> list[TaskResponse]:
        return GLOBAL_RELAYS[relay_id]

    def has_relay(self, relay_id: uuid.UUID) -> bool:
        return relay_id in GLOBAL_RELAYS
