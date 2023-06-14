#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from functools import cache

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import Encoding, load_pem_private_key
from cryptography.x509 import (
    BasicConstraints,
    Certificate,
    CertificateBuilder,
    CertificateSigningRequest,
    DNSName,
    load_pem_x509_certificate,
    random_serial_number,
    SubjectAlternativeName,
)
from cryptography.x509.oid import NameOID
from dateutil.relativedelta import relativedelta

from .site_context import agent_ca_path, site_ca_path


def site_root_certificate() -> Certificate:
    return load_pem_x509_certificate(site_ca_path().read_bytes())


def sign_agent_csr(
    csr: CertificateSigningRequest,
    lifetime_in_months: int,
    keypair: tuple[Certificate, RSAPrivateKey],
) -> Certificate:
    root_cert, root_key = keypair
    return (
        (
            CertificateBuilder()
            .subject_name(csr.subject)
            .public_key(csr.public_key())
            .serial_number(random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + relativedelta(months=lifetime_in_months))
        )
        .issuer_name(root_cert.issuer)
        .add_extension(
            SubjectAlternativeName([DNSName(extract_cn_from_csr(csr))]),
            critical=False,
        )
        .add_extension(
            BasicConstraints(
                ca=False,
                path_length=None,
            ),
            critical=True,
        )
        .sign(
            root_key,
            SHA256(),
        )
    )


def serialize_to_pem(certificate: Certificate | CertificateSigningRequest) -> str:
    return certificate.public_bytes(Encoding.PEM).decode()


def extract_cn_from_csr(csr: CertificateSigningRequest) -> str:
    return csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value


@cache
def agent_root_ca() -> tuple[Certificate, RSAPrivateKey]:
    pem_bytes = agent_ca_path().read_bytes()
    return load_pem_x509_certificate(pem_bytes), load_pem_private_key(pem_bytes, None)
