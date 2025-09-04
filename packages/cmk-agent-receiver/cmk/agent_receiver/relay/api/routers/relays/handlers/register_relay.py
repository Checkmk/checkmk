#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
from uuid import uuid4

from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID


@dataclasses.dataclass
class RegisterRelayHandler:
    relays_repository: RelaysRepository

    def process(self) -> RelayID:
        return self._add_registry()

    def _add_registry(self) -> RelayID:
        relay_id = RelayID(str(uuid4()))
        while self.relays_repository.has_relay(relay_id):
            relay_id = RelayID(str(uuid4()))

        self.relays_repository.add_relay(relay_id)
        return relay_id
