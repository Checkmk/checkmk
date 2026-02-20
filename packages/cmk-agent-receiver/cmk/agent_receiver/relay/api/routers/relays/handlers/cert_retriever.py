#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import Final

from cryptography.x509 import CertificateSigningRequest

from cmk.agent_receiver.lib import certs as certslib
from cmk.agent_receiver.relay.lib.shared_types import CertificateCNError, RelayID

_VALIDITY_IN_MONTHS: Final = 3


@dataclasses.dataclass(frozen=True)
class Certificates:
    root_cert: str
    client_cert: str


def get_certificates(csr: str, relay_id: RelayID) -> Certificates:
    validated_csr = _validate_csr(csr, relay_id)
    root_cert = _get_root_cert()
    client_cert = _sign_csr(validated_csr)
    return Certificates(root_cert, client_cert)


def _get_root_cert() -> str:
    return certslib.serialize_to_pem(certslib.site_root_certificate())


def _sign_csr(csr: CertificateSigningRequest) -> str:
    return certslib.serialize_to_pem(
        certslib.sign_csr(
            csr=csr,
            lifetime_in_months=_VALIDITY_IN_MONTHS,
            keypair=certslib.relay_root_ca(),
            valid_from=certslib.current_time_naive(),
        )
    )


def _validate_csr(csr: str, relay_id: RelayID) -> CertificateSigningRequest:
    csr_obj = certslib.validate_csr(csr)
    cn = certslib.extract_cn_from_csr(csr_obj)
    rid = str(relay_id)
    if cn != rid:
        raise CertificateCNError(expected_cn=rid, actual_cn=cn)
    return csr_obj
