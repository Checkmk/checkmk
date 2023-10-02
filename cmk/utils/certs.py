#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, NamedTuple

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
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
    load_pem_x509_certificate,
    Name,
    NameAttribute,
    random_serial_number,
    SubjectAlternativeName,
)
from cryptography.x509.oid import NameOID
from dateutil.relativedelta import relativedelta

from livestatus import SiteId

from cmk.utils.crypto.certificate import CertificateWithPrivateKey, RsaPrivateKey


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

_DEFAULT_VALIDITY = relativedelta(years=10)
_DEFAULT_KEY_SIZE = 4096


class RootCA(NamedTuple):
    cert: Certificate
    rsa: RSAPrivateKey

    @classmethod
    def load(cls, path: Path) -> RootCA:
        return cls(*load_cert_and_private_key(path))

    @classmethod
    def load_or_create(
        cls,
        path: Path,
        name: str,
        validity: relativedelta = _DEFAULT_VALIDITY,
        key_size: int = _DEFAULT_KEY_SIZE,
    ) -> RootCA:
        try:
            return cls.load(path)
        except FileNotFoundError:
            cert, rsa = _generate_root_cert(name, validity, key_size)
            _save_cert_chain(path, [cert], rsa)
        return cls(cert, rsa)

    def sign_csr(
        self,
        csr: CertificateSigningRequest,
        validity: relativedelta = _DEFAULT_VALIDITY,
    ) -> Certificate:
        return _sign_csr(csr, validity, self.cert, self.rsa)

    def save_new_signed_cert(
        self, path: Path, name: str, validity: relativedelta = _DEFAULT_VALIDITY
    ) -> None:
        private_key = RsaPrivateKey.generate(_DEFAULT_KEY_SIZE)._key
        cert = _sign_csr(
            _make_csr(
                _make_subject_name(name),
                private_key,
            ),
            validity,
            self.cert,
            self.rsa,
        )

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


def load_cert_and_private_key(path_pem: Path) -> tuple[Certificate, RSAPrivateKey]:
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
    key: RSAPrivateKey,
) -> None:
    path_pem.parent.mkdir(mode=0o770, parents=True, exist_ok=True)
    with path_pem.open(mode="wb") as f:
        # RSAPrivateKeyWithSerialization confuses mypy, RSAPrivateKey has private_bytes
        private_bytes = key.private_bytes(  # type:ignore[attr-defined]
            Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
        )
        f.write(private_bytes)
        for cert in certificate_chain:
            f.write(cert.public_bytes(Encoding.PEM))
    path_pem.chmod(mode=0o660)


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
        # use naive datetimes -- see cmk.utils.crypto.certificate.Certificate._naive_utcnow
        .not_valid_before(datetime.now(tz=timezone.utc).replace(tzinfo=None))
        .not_valid_after(datetime.now(tz=timezone.utc).replace(tzinfo=None) + validity)
    )


def _generate_root_cert(
    common_name: str,
    validity: relativedelta,
    key_size: int,
) -> tuple[Certificate, RSAPrivateKey]:
    ca = CertificateWithPrivateKey.generate_self_signed(
        common_name=common_name,
        expiry=validity,
        key_size=key_size,
        is_ca=True,
    )
    return (ca.certificate._cert, ca.private_key._key)


def _make_csr(
    subject_name: Name,
    private_key: RSAPrivateKey,
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
    signing_private_key: RSAPrivateKey,
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
