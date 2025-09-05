#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses

from pydantic import SecretStr

from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID


class RelayNotFoundError(Exception):
    """Exception raised when a relay is not found in the registry."""


@dataclasses.dataclass
class UnregisterRelayHandler:
    relays_repository: RelaysRepository

    def process(self, relay_id: RelayID, authorization: SecretStr) -> None:
        if not self.relays_repository.has_relay(relay_id, authorization):
            raise RelayNotFoundError(f"Relay ID {relay_id} is not registered.")

        self.relays_repository.remove_relay(relay_id, authorization)
