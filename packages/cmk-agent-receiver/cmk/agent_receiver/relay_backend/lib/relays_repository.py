import dataclasses
import threading
import uuid

from cmk.relay_protocols.tasks import TaskResponse

GLOBAL_RELAYS: dict[uuid.UUID, list[TaskResponse]] = {}
GLOBAL_RELAYS_LOCK = threading.RLock()


@dataclasses.dataclass
class RelaysRepository:
    def add_relay(self, relay_id: uuid.UUID) -> None:
        with GLOBAL_RELAYS_LOCK:
            GLOBAL_RELAYS[relay_id] = []

    def list_relays(self) -> list[uuid.UUID]:
        with GLOBAL_RELAYS_LOCK:
            return list(GLOBAL_RELAYS.keys())

    def get_relay_tasks(self, relay_id: uuid.UUID) -> list[TaskResponse]:
        with GLOBAL_RELAYS_LOCK:
            return GLOBAL_RELAYS[relay_id]

    def has_relay(self, relay_id: uuid.UUID) -> bool:
        with GLOBAL_RELAYS_LOCK:
            return relay_id in GLOBAL_RELAYS
