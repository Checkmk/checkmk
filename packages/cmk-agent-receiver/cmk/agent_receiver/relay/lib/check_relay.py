#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

import fastapi

from cmk.agent_receiver.relay.api.dependencies.relays_repository import get_relays_repository
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID, RelayNotFoundError
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth


def check_relay(
    relay_id: RelayID,
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> None:
    auth = InternalAuth()
    if not relays_repository.has_relay(relay_id, auth):
        raise RelayNotFoundError(relay_id)
