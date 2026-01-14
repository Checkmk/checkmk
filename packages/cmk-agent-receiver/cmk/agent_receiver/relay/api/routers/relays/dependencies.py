#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

import fastapi

from cmk.agent_receiver.lib.config import Config, get_config
from cmk.agent_receiver.relay.api.dependencies.relays_repository import (
    get_relays_repository,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers import (
    ForwardMonitoringDataHandler,
    RefreshCertHandler,
    RegisterRelayHandler,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


def get_refresh_cert_handler(
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> RefreshCertHandler:
    return RefreshCertHandler(relays_repository=relays_repository)


def get_register_relay_handler(
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> RegisterRelayHandler:
    return RegisterRelayHandler(relays_repository=relays_repository)


def get_forward_monitoring_data_handler(
    config: Annotated[Config, fastapi.Depends(get_config)],
) -> ForwardMonitoringDataHandler:
    return ForwardMonitoringDataHandler(data_socket=config.raw_data_socket)
