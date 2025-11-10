#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses

from cryptography.x509 import load_pem_x509_csr
from pydantic import SecretStr

from cmk.agent_receiver.lib.certs import (
    agent_root_ca,
    current_time_naive,
    serialize_to_pem,
    sign_csr,
    site_root_certificate,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.agent_receiver.relay.lib.site_auth import UserAuth
from cmk.relay_protocols.relays import RelayRegistrationRequest, RelayRegistrationResponse


@dataclasses.dataclass
class RegisterRelayHandler:
    relays_repository: RelaysRepository

    @staticmethod
    def get_root_cert() -> str:
        return serialize_to_pem(site_root_certificate())

    @staticmethod
    def sign_csr(csr: str) -> str:
        return serialize_to_pem(
            sign_csr(
                csr=load_pem_x509_csr(csr.encode()),
                lifetime_in_months=15,
                keypair=agent_root_ca(),
                valid_from=current_time_naive(),
            )
        )

    def process(
        self, authorization: SecretStr, request: RelayRegistrationRequest
    ) -> RelayRegistrationResponse:
        # Important: First authenticate
        auth = UserAuth(authorization)
        # Then sign the CSR
        root_cert = self.get_root_cert()
        client_cert = self.sign_csr(request.csr)
        # before relay registration
        relay_id = self.relays_repository.add_relay(auth, RelayID(request.relay_id), request.alias)

        return RelayRegistrationResponse(
            relay_id=relay_id, root_cert=root_cert, client_cert=client_cert
        )
