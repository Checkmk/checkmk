#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta
from pathlib import Path
from typing import Final, Iterable, Tuple, Union

from cryptography.hazmat.primitives.asymmetric.rsa import (
    generate_private_key,
    RSAPrivateKeyWithSerialization,
    RSAPublicKey,
)
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    load_pem_private_key,
    NoEncryption,
    PrivateFormat,
)
from cryptography.x509 import (
    BasicConstraints,
    Certificate,
    CertificateBuilder,
    CertificateSigningRequest,
    CertificateSigningRequestBuilder,
    DNSName,
    KeyUsage,
    load_pem_x509_certificate,
    Name,
    NameAttribute,
    random_serial_number,
    SubjectAlternativeName,
    SubjectKeyIdentifier,
)
from cryptography.x509.oid import NameOID

from cmk.utils.paths import omd_root


class RootCA:
    def __init__(self, path: Path, name: str, days_valid: int = 999 * 365) -> None:
        try:
            cert, rsa = load_cert_and_private_key(path)
        except FileNotFoundError:
            rsa = _make_private_key()
            cert = _make_root_certificate(_make_subject_name(name), days_valid, rsa)
            _save_cert_chain(path, [cert], rsa)

        self.cert: Final = cert
        self.rsa: Final = rsa
        self.days_valid: Final = days_valid

    def new_signed_cert(
        self,
        name: str,
        days_valid: int,
    ) -> Tuple[Certificate, RSAPrivateKeyWithSerialization]:
        private_key = _make_private_key()
        cert = _sign_csr(
            _make_csr(
                _make_subject_name(name),
                private_key,
            ),
            days_valid,
            self.cert,
            self.rsa,
        )
        return cert, private_key

    def save_new_signed_cert(self, path: Path, name: str, days_valid: int) -> None:
        cert, private_key = self.new_signed_cert(name, days_valid)
        _save_cert_chain(path, [cert, self.cert], private_key)


def cert_dir(site_root_dir: Path) -> Path:
    return site_root_dir / "etc" / "ssl"


def root_cert_path(ca_dir: Path) -> Path:
    return ca_dir / "ca.pem"


def load_cert_and_private_key(path_pem: Path) -> Tuple[Certificate, RSAPrivateKeyWithSerialization]:
    return (
        load_pem_x509_certificate(
            pem_bytes := path_pem.read_bytes(),
        ),
        load_pem_private_key(
            pem_bytes,
            None,
        ),
    )


def _save_cert_chain(
    path_pem: Path,
    certificate_chain: Iterable[Certificate],
    key: RSAPrivateKeyWithSerialization,
) -> None:
    path_pem.parent.mkdir(mode=0o770, parents=True, exist_ok=True)
    with path_pem.open(mode="wb") as f:
        f.write(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
        for cert in certificate_chain:
            f.write(cert.public_bytes(Encoding.PEM))
    path_pem.chmod(mode=0o660)


def load_local_ca() -> Tuple[Certificate, RSAPrivateKeyWithSerialization]:
    return load_cert_and_private_key(root_cert_path(cert_dir(Path(omd_root))))


def _make_private_key() -> RSAPrivateKeyWithSerialization:
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


def _make_root_certificate(
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


def _make_csr(
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


def _sign_csr(
    csr: CertificateSigningRequest,
    days_valid: int,
    signing_cert: Certificate,
    signing_private_key: RSAPrivateKeyWithSerialization,
) -> Certificate:
    common_name = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    return (
        _make_cert_builder(
            csr.subject,
            days_valid,
            _rsa_public_key_from_cert_or_csr(csr),
        )
        .issuer_name(signing_cert.issuer)
        .add_extension(
            SubjectAlternativeName([DNSName(common_name)]),
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
            signing_private_key,
            SHA256(),
        )
    )


def sign_csr_with_local_ca(
    csr: CertificateSigningRequest,
    days_valid: int,
) -> Certificate:
    return _sign_csr(
        csr,
        days_valid,
        *load_local_ca(),
    )


def _make_subject_name(cn: str) -> Name:
    return Name(
        [
            NameAttribute(
                NameOID.COMMON_NAME,
                cn,
            ),
        ]
    )


def _rsa_public_key_from_cert_or_csr(
    c: Union[Certificate, CertificateSigningRequest],
    /,
) -> RSAPublicKey:
    assert isinstance(
        public_key := c.public_key(),
        RSAPublicKey,
    )
    return public_key
