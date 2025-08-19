#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

import fastapi

from cmk.agent_receiver.relay.api.dependencies.relays_repository import (
    get_relays_repository,
)
from cmk.agent_receiver.relay.api.routers.tasks.handlers import (
    GetRelayTasksHandler,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


def get_relay_tasks_handler(
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> GetRelayTasksHandler:
    return GetRelayTasksHandler(relays_repository=relays_repository)
