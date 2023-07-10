#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Final, NamedTuple

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
from dateutil.relativedelta import relativedelta

from livestatus import SiteId


class _CNTemplate:
    """Template used to create the certs CN containing the sites name"""

    def __init__(self, template: str) -> None:
        self._temp = template
        self._match = re.compile("CN=" + template % "([^=+,]*)").match

    def format(self, site: SiteId | str) -> str:
        return self._temp % site

    def extract_site(self, rfc4514_string: str) -> SiteId | None:
        return None if (m := self._match(rfc4514_string)) is None else SiteId(m.group(1))


CN_TEMPLATE = _CNTemplate("Site '%s' local CA")

_DEFAULT_VALIDITY = relativedelta(years=999)


class RootCA(NamedTuple):
    cert: Certificate
    rsa: RSAPrivateKeyWithSerialization

    @classmethod
    def load(cls, path: Path) -> RootCA:
        return cls(*load_cert_and_private_key(path))

    @classmethod
    def load_or_create(
        cls, path: Path, name: str, validity: relativedelta = _DEFAULT_VALIDITY
    ) -> RootCA:
        try:
            return cls.load(path)
        except FileNotFoundError:
            rsa = _make_private_key()
            cert = _make_root_certificate(_make_subject_name(name), validity, rsa)
            _save_cert_chain(path, [cert], rsa)
        return cls(cert, rsa)

    def sign_csr(
        self,
        csr: CertificateSigningRequest,
        validity: relativedelta = _DEFAULT_VALIDITY,
    ) -> Certificate:
        return _sign_csr(csr, validity, self.cert, self.rsa)

    def new_signed_cert(
        self,
        name: str,
        validity: relativedelta = _DEFAULT_VALIDITY,
    ) -> tuple[Certificate, RSAPrivateKeyWithSerialization]:
        private_key = _make_private_key()
        cert = _sign_csr(
            _make_csr(
                _make_subject_name(name),
                private_key,
            ),
            validity,
            self.cert,
            self.rsa,
        )
        return cert, private_key

    def save_new_signed_cert(
        self, path: Path, name: str, validity: relativedelta = _DEFAULT_VALIDITY
    ) -> None:
        cert, private_key = self.new_signed_cert(name, validity)
        _save_cert_chain(path, [cert, self.cert], private_key)


def cert_dir(site_root_dir: Path) -> Path:
    return site_root_dir / "etc" / "ssl"


def root_cert_path(ca_dir: Path) -> Path:
    return ca_dir / "ca.pem"


def write_cert_store(source_dir: Path, store_path: Path) -> None:
    """Extract certificate part out of PEM files and concat
    to single cert store file."""
    pem_certs = (
        load_pem_x509_certificate(pem_path.read_bytes()).public_bytes(Encoding.PEM)
        for pem_path in source_dir.glob("*.pem")
    )
    store_path.write_bytes(b"".join(pem_certs))


def load_cert_and_private_key(path_pem: Path) -> tuple[Certificate, RSAPrivateKeyWithSerialization]:
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


def _make_private_key() -> RSAPrivateKeyWithSerialization:
    return generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


def _make_cert_builder(
    subject_name: Name,
    validity: relativedelta,
    public_key: RSAPublicKey,
) -> CertificateBuilder:
    return (
        CertificateBuilder()
        .subject_name(subject_name)
        .public_key(public_key)
        .serial_number(random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + validity)
    )


def _make_root_certificate(
    subject_name: Name,
    validity: relativedelta,
    private_key: RSAPrivateKeyWithSerialization,
) -> Certificate:
    return (
        _make_cert_builder(
            subject_name,
            validity,
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
    validity: relativedelta,
    signing_cert: Certificate,
    signing_private_key: RSAPrivateKeyWithSerialization,
) -> Certificate:
    common_name = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    return (
        _make_cert_builder(
            csr.subject,
            validity,
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
    c: Certificate | CertificateSigningRequest,
    /,
) -> RSAPublicKey:
    assert isinstance(
        public_key := c.public_key(),
        RSAPublicKey,
    )
    return public_key


class RemoteSiteCertsStore:
    def __init__(self, path: Path) -> None:
        self.path: Final = path

    def save(self, site_id: SiteId, cert: Certificate) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        self._make_file_name(site_id).write_bytes(cert.public_bytes(Encoding.PEM))

    def load(self, site_id: SiteId) -> Certificate:
        return load_pem_x509_certificate(self._make_file_name(site_id).read_bytes())

    def _make_file_name(self, site_id: SiteId) -> Path:
        return self.path / f"{site_id}.pem"
