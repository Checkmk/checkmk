#!/usr/bin/env python3
from typing import Annotated

import fastapi

from cmk.agent_receiver.config import Config, get_config
from cmk.agent_receiver.relay.api.dependencies.relays_repository import (
    get_relays_repository,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers import (
    ForwardMonitoringDataHandler,
    RegisterRelayHandler,
    UnregisterRelayHandler,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


def get_register_relay_handler(
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> RegisterRelayHandler:
    return RegisterRelayHandler(relays_repository=relays_repository)


def get_unregister_relay_handler(
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> UnregisterRelayHandler:
    return UnregisterRelayHandler(relays_repository=relays_repository)


def get_forward_monitoring_data_handler(
    config: Annotated[Config, fastapi.Depends(get_config)],
) -> ForwardMonitoringDataHandler:
    return ForwardMonitoringDataHandler(data_socket=config.raw_data_socket)
