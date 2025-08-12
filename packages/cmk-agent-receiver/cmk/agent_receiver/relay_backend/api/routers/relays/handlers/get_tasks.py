import dataclasses
from uuid import UUID

from cmk.agent_receiver.relay_backend.api.routers.relays.handlers.register import RELAY_REGISTRY
from cmk.relay_protocols.tasks import TaskListResponse, TaskStatus


class RelayNotFoundError(Exception):
    """Exception raised when a relay is not found in the registry."""

    pass


@dataclasses.dataclass
class GetRelayTasksHandler:
    def process(self, relay_id: UUID, status: TaskStatus | None) -> TaskListResponse:
        return self._get_tasks(relay_id, status)

    def _get_tasks(self, relay_id: UUID, status: TaskStatus | None) -> TaskListResponse:
        if relay_id not in RELAY_REGISTRY:
            raise RelayNotFoundError(f"Relay with ID {relay_id} not found")

        tasks = [task for task in RELAY_REGISTRY[relay_id] if task.status == status]
        return TaskListResponse(tasks=tasks)
