#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.hashes import SHA512
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import (
    Certificate,
    CertificateSigningRequest,
    CertificateSigningRequestBuilder,
    load_pem_x509_certificate,
    Name,
    NameAttribute,
)
from cryptography.x509.oid import NameOID
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from cmk.utils.crypto.certificate import CertificateWithPrivateKey, RsaPrivateKey


def check_certificate_against_private_key(
    cert: Certificate,
    private_key: rsa.RSAPrivateKey,
) -> None:
    # Check if the public key of certificate matches the public key corresponding to the given
    # private one
    pubkey = cert.public_key()
    assert isinstance(pubkey, rsa.RSAPublicKey)
    assert pubkey.public_numbers() == private_key.public_key().public_numbers()


def get_cn(name: Name) -> str | bytes:
    cn = name.get_attributes_for_oid(NameOID.COMMON_NAME)
    assert len(cn) == 1
    return cn[0].value


def check_cn(cert_or_csr: Certificate | CertificateSigningRequest, expected_cn: str) -> bool:
    return get_cn(cert_or_csr.subject) == expected_cn


def generate_csr_pair(
    cn: str, private_key_size: int = 2048
) -> tuple[rsa.RSAPrivateKey, CertificateSigningRequest]:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,
    )
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
            SHA512(),
        ),
    )


def load_cert_and_private_key(path_pem: Path) -> tuple[Certificate, rsa.RSAPrivateKey]:
    return (
        load_pem_x509_certificate(
            pem_bytes := path_pem.read_bytes(),
        ),
        load_pem_private_key(
            pem_bytes,
            None,
        ),
    )


@pytest.fixture(name="self_signed_cert", scope="module")
def fixture_self_signed() -> CertificateWithPrivateKey:
    """
    Return a self-signed certificate.

    Valid from 2023-01-01 08:00:00 til 2023-01-01 10:00:00.
    """
    with freeze_time(datetime(2023, 1, 1, 8, 0, 0)):
        return CertificateWithPrivateKey.generate_self_signed(
            common_name="TestGenerateSelfSigned",
            expiry=relativedelta(hours=2),
            key_size=1024,
            is_ca=True,
        )


@pytest.fixture(name="rsa_key", scope="module")
def fixture_rsa_key() -> RsaPrivateKey:
    return RsaPrivateKey.generate(1024)
