#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses

from cryptography.x509 import CertificateSigningRequest
from pydantic import SecretStr

from cmk.agent_receiver.lib.certs import (
    current_time_naive,
    extract_cn_from_csr,
    relay_root_ca,
    serialize_to_pem,
    sign_csr,
    site_root_certificate,
    validate_csr,
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
    def sign_csr(csr: CertificateSigningRequest) -> str:
        return serialize_to_pem(
            sign_csr(
                csr=csr,
                lifetime_in_months=15,
                keypair=relay_root_ca(),
                valid_from=current_time_naive(),
            )
        )

    @staticmethod
    def validate_csr(csr: str, relay_id: RelayID) -> CertificateSigningRequest:
        csr_obj = validate_csr(csr)
        cn = extract_cn_from_csr(csr_obj)
        if cn != relay_id:
            raise ValueError("CN does not match relay ID")
        return csr_obj

    def process(
        self, authorization: SecretStr, request: RelayRegistrationRequest
    ) -> RelayRegistrationResponse:
        relay_id = RelayID(request.relay_id)
        # Important: First authenticate
        auth = UserAuth(authorization)

        root_cert = ""
        client_cert = ""

        csr = self.validate_csr(request.csr, relay_id)
        # Then sign the CSR
        root_cert = self.get_root_cert()
        client_cert = self.sign_csr(csr)

        # before relay registration
        self.relays_repository.add_relay(auth, relay_id, request.alias)

        return RelayRegistrationResponse(
            relay_id=relay_id, root_cert=root_cert, client_cert=client_cert
        )
