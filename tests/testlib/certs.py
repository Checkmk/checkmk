#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.asymmetric.rsa import (
    generate_private_key,
    RSAPrivateKey,
    RSAPublicKey,
)
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.x509 import (
    Certificate,
    CertificateSigningRequest,
    CertificateSigningRequestBuilder,
    Name,
    NameAttribute,
)
from cryptography.x509.oid import NameOID
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from cmk.utils.certs import _rsa_public_key_from_cert_or_csr
from cmk.utils.crypto.certificate import CertificateWithPrivateKey


def check_certificate_against_private_key(
    cert: Certificate,
    private_key: RSAPrivateKey,
) -> None:
    # Check if the public key of certificate matches the public key corresponding to the given
    # private one
    assert (
        _rsa_public_key_from_cert_or_csr(cert).public_numbers()
        == private_key.public_key().public_numbers()
    )


def check_certificate_against_public_key(
    cert: Certificate,
    public_key: RSAPublicKey,
) -> None:
    # Check if the signature of the certificate matches the public key
    public_key.verify(
        cert.signature,
        cert.tbs_certificate_bytes,
        PKCS1v15(),
        SHA256(),
    )


def check_cn(
    cert_or_csr: Certificate | CertificateSigningRequest,
    expected_cn: str,
) -> bool:
    return cert_or_csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == expected_cn


def generate_csr_pair(
    cn: str, private_key_size: int = 2048
) -> tuple[RSAPrivateKey, CertificateSigningRequest]:
    private_key = _generate_private_key(private_key_size)
    return (
        private_key,
        CertificateSigningRequestBuilder()
        .subject_name(
            Name(
                [
                    NameAttribute(NameOID.COMMON_NAME, cn),
                ]
            )
        )
        .sign(
            private_key,
            SHA256(),
        ),
    )


def _generate_private_key(size: int) -> RSAPrivateKey:
    return generate_private_key(
        public_exponent=65537,
        key_size=size,
    )


FROZEN_NOW = datetime(2023, 1, 1, 8, 0, 0)


@pytest.fixture(name="self_signed_cert", scope="module")
def fixture_self_signed() -> CertificateWithPrivateKey:
    """
    Return a self-signed certificate.

    Valid from 2023-01-01 08:00:00 til 2023-01-01 10:00:00.
    """
    with freeze_time(FROZEN_NOW):
        return CertificateWithPrivateKey.generate_self_signed(
            common_name="TestGenerateSelfSigned",
            expiry=relativedelta(hours=2),
            key_size=1024,
        )
