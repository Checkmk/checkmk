#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses

from pydantic import SecretStr

from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.agent_receiver.relay.lib.site_auth import UserAuth


@dataclasses.dataclass
class RegisterRelayHandler:
    relays_repository: RelaysRepository

    def process(self, authorization: SecretStr, alias: str) -> RelayID:
        auth = UserAuth(authorization)
        return self.relays_repository.add_relay(auth, alias)
