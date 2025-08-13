from typing import Annotated

import fastapi

from cmk.agent_receiver.relay_backend.api.dependencies.relays_repository import (
    get_relays_repository,
)
from cmk.agent_receiver.relay_backend.api.routers.relays.handlers.get_relay_tasks import (
    GetRelayTasksHandler,
)
from cmk.agent_receiver.relay_backend.lib.relays_repository import RelaysRepository


def get_relay_tasks_handler(
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> GetRelayTasksHandler:
    return GetRelayTasksHandler(relays_repository=relays_repository)
