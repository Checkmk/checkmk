#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Union

from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.x509 import Certificate, CertificateSigningRequest
from cryptography.x509.oid import NameOID

from cmk.utils.certs import _rsa_public_key_from_cert_or_csr


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
    cert_or_csr: Union[Certificate, CertificateSigningRequest],
    expected_cn: str,
) -> bool:
    return cert_or_csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == expected_cn
