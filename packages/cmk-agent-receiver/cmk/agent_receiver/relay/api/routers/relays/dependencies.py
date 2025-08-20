from typing import Annotated

import fastapi

from cmk.agent_receiver.relay.api.dependencies.relays_repository import (
    get_relays_repository,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers import (
    GetRelayTasksHandler,
    RegisterRelayHandler,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


def get_relay_tasks_handler(
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> GetRelayTasksHandler:
    return GetRelayTasksHandler(relays_repository=relays_repository)


def get_register_relay_handler(
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> RegisterRelayHandler:
    return RegisterRelayHandler(relays_repository=relays_repository)
