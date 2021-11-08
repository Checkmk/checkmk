#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, Union

from cryptography.hazmat.primitives.asymmetric.rsa import (
    generate_private_key,
    RSAPrivateKeyWithSerialization,
    RSAPublicKey,
)
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import (
    BasicConstraints,
    Certificate,
    CertificateBuilder,
    CertificateSigningRequest,
    CertificateSigningRequestBuilder,
    KeyUsage,
    load_pem_x509_certificate,
    Name,
    NameAttribute,
    random_serial_number,
    SubjectKeyIdentifier,
)
from cryptography.x509.oid import NameOID

from cmk.utils.paths import omd_root


def cert_dir(site_root_dir: Path) -> Path:
    return site_root_dir / "etc" / "ssl"


def root_cert_path(ca_dir: Path) -> Path:
    return ca_dir / "ca.pem"


def load_cert_and_private_key(path_pem: Path) -> Tuple[Certificate, RSAPrivateKeyWithSerialization]:
    return (
        load_pem_x509_certificate(
            pem_bytes := (path_pem).read_bytes(),
        ),
        load_pem_private_key(
            pem_bytes,
            None,
        ),
    )


def load_local_ca() -> Tuple[Certificate, RSAPrivateKeyWithSerialization]:
    return load_cert_and_private_key(root_cert_path(cert_dir(Path(omd_root))))


def make_private_key() -> RSAPrivateKeyWithSerialization:
    return generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


def _make_cert_builder(
    subject_name: Name,
    days_valid: int,
    public_key: RSAPublicKey,
) -> CertificateBuilder:
    return (
        CertificateBuilder()
        .subject_name(subject_name)
        .public_key(public_key)
        .serial_number(random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=days_valid))
    )


def make_root_certificate(
    subject_name: Name,
    days_valid: int,
    private_key: RSAPrivateKeyWithSerialization,
) -> Certificate:
    return (
        _make_cert_builder(
            subject_name,
            days_valid,
            private_key.public_key(),
        )
        .issuer_name(subject_name)
        .add_extension(
            SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        )
        .add_extension(
            BasicConstraints(
                ca=True,
                path_length=0,
            ),
            critical=True,
        )
        .add_extension(
            KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(
            private_key,
            SHA256(),
        )
    )


def make_csr(
    subject_name: Name,
    private_key: RSAPrivateKeyWithSerialization,
) -> CertificateSigningRequest:
    return (
        CertificateSigningRequestBuilder()
        .subject_name(subject_name)
        .sign(
            private_key,
            SHA256(),
        )
    )


def sign_csr(
    csr: CertificateSigningRequest,
    days_valid: int,
    signing_cert: Certificate,
    signing_private_key: RSAPrivateKeyWithSerialization,
) -> Certificate:
    return (
        _make_cert_builder(
            csr.subject,
            days_valid,
            rsa_public_key_from_cert_or_csr(csr),
        )
        .issuer_name(signing_cert.issuer)
        .sign(
            signing_private_key,
            SHA256(),
        )
    )


def sign_csr_with_local_ca(
    csr: CertificateSigningRequest,
    days_valid: int,
) -> Certificate:
    return sign_csr(
        csr,
        days_valid,
        *load_local_ca(),
    )


def make_subject_name(cn: str) -> Name:
    return Name(
        [
            NameAttribute(
                NameOID.COMMON_NAME,
                cn,
            ),
        ]
    )


def rsa_public_key_from_cert_or_csr(
    c: Union[Certificate, CertificateSigningRequest],
    /,
) -> RSAPublicKey:
    assert isinstance(
        public_key := c.public_key(),
        RSAPublicKey,
    )
    return public_key
