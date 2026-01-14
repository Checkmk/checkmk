#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses

from pydantic import SecretStr

from cmk.agent_receiver.relay.api.routers.relays.handlers.cert_retriever import get_certificates
from cmk.agent_receiver.relay.lib.relays_repository import (
    RelayNotFoundError,
    RelaysRepository,
)
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth, UserAuth
from cmk.relay_protocols import relays as relay_protocols


@dataclasses.dataclass
class RegisterRelayHandler:
    relays_repository: RelaysRepository

    def process(
        self, authorization: SecretStr, request: relay_protocols.RelayRegistrationRequest
    ) -> relay_protocols.RelayRegistrationResponse:
        relay_id = RelayID(request.relay_id)
        # Important: First authenticate
        auth = UserAuth(authorization)

        certificates = get_certificates(request.csr, relay_id)

        # before relay registration
        self.relays_repository.add_relay(auth, relay_id, request.alias)

        return relay_protocols.RelayRegistrationResponse(
            relay_id=relay_id,
            root_cert=certificates.root_cert,
            client_cert=certificates.client_cert,
        )


@dataclasses.dataclass
class RefreshCertHandler:
    relays_repository: RelaysRepository

    def process(
        self, relay_id: RelayID, request: relay_protocols.RelayRefreshCertRequest
    ) -> relay_protocols.RelayRefreshCertResponse:
        auth = InternalAuth()
        if not self.relays_repository.relay_exists(auth, relay_id):
            raise RelayNotFoundError(relay_id)
        certificates = get_certificates(request.csr, relay_id)
        return relay_protocols.RelayRefreshCertResponse(
            root_cert=certificates.root_cert,
            client_cert=certificates.client_cert,
        )
