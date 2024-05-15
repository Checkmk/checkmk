#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.x509 import (
    Certificate,
    CertificateSigningRequest,
    CertificateSigningRequestBuilder,
    Name,
    NameAttribute,
)
from cryptography.x509.oid import NameOID


# Copied from test/testlib/certs.py to make cmk-agent-receiver/tests self contained
def generate_csr_pair(
    cn: str, private_key_size: int = 2048
) -> tuple[rsa.RSAPrivateKey, CertificateSigningRequest]:
    private_key = generate_private_key(private_key_size)
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


# Copied from test/testlib/certs.py to make cmk-agent-receiver/tests self contained
def generate_private_key(size: int) -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=size,
    )


# Copied from test/testlib/certs.py to make cmk-agent-receiver/tests self contained
def check_cn(cert_or_csr: Certificate | CertificateSigningRequest, expected_cn: str) -> bool:
    return get_cn(cert_or_csr.subject) == expected_cn


# Copied from test/testlib/certs.py to make cmk-agent-receiver/tests self contained
def get_cn(name: Name) -> str | bytes:
    cn = name.get_attributes_for_oid(NameOID.COMMON_NAME)
    assert len(cn) == 1
    return cn[0].value


# Copied from test/testlib/certs.py to make cmk-agent-receiver/tests self contained
def check_certificate_against_private_key(
    cert: Certificate,
    private_key: rsa.RSAPrivateKey,
) -> None:
    # Check if the public key of certificate matches the public key corresponding to the given
    # private one
    assert (
        _rsa_public_key_from_cert_or_csr(cert).public_numbers()
        == private_key.public_key().public_numbers()
    )


# Copied from cmk/utils/certs.py to make cmk-agent-receiver/tests self contained
def _rsa_public_key_from_cert_or_csr(
    c: Certificate | CertificateSigningRequest,
    /,
) -> RSAPublicKey:
    assert isinstance(
        public_key := c.public_key(),
        RSAPublicKey,
    )
    return public_key


# Copied from test/testlib/certs.py to make cmk-agent-receiver/tests self contained
def check_certificate_against_public_key(
    cert: Certificate,
    public_key: rsa.RSAPublicKey,
) -> None:
    # Check if the signature of the certificate matches the public key
    assert cert.signature_hash_algorithm is not None
    public_key.verify(
        cert.signature,
        cert.tbs_certificate_bytes,
        PKCS1v15(),
        cert.signature_hash_algorithm,
    )
