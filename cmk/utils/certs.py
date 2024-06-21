#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding, load_pem_private_key
from dateutil.relativedelta import relativedelta

from livestatus import SiteId

from cmk.utils.crypto.certificate import (
    Certificate,
    CertificateSigningRequest,
    CertificateWithPrivateKey,
    X509Name,
)
from cmk.utils.crypto.keys import is_supported_private_key_type, PrivateKey
from cmk.utils.crypto.types import HashAlgorithm
from cmk.utils.log.security_event import SecurityEvent
from cmk.utils.site import omd_site
from cmk.utils.user import UserId


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


class RootCA(CertificateWithPrivateKey):
    @classmethod
    def load(cls, path: Path) -> RootCA:
        cert = x509.load_pem_x509_certificate(pem_bytes := path.read_bytes())
        key = load_pem_private_key(pem_bytes, None)
        if not is_supported_private_key_type(key):
            raise ValueError(f"Unsupported private key type {type(key)}")
        return cls(certificate=Certificate(cert), private_key=PrivateKey(key))

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
            ca = CertificateWithPrivateKey.generate_self_signed(
                common_name=name,
                organization=f"Checkmk Site {omd_site()}",
                expiry=validity,
                key_size=key_size,
                is_ca=True,
            )
            _save_cert_chain(path, [ca.certificate], ca.private_key)
            return cls(ca.certificate, ca.private_key)

    def issue_new_certificate(
        self,
        common_name: str,
        validity: relativedelta = _DEFAULT_VALIDITY,
        key_size: int = _DEFAULT_KEY_SIZE,
    ) -> tuple[Certificate, PrivateKey]:
        new_cert_key = PrivateKey.generate_rsa(key_size)
        new_cert_csr = CertificateSigningRequest.create(
            subject_name=X509Name.create(common_name=common_name),
            subject_private_key=new_cert_key,
        )
        return self.sign_csr(new_cert_csr, validity), new_cert_key

    def issue_and_store_certificate(
        self,
        path: Path,
        common_name: str,
        validity: relativedelta = _DEFAULT_VALIDITY,
        key_size: int = _DEFAULT_KEY_SIZE,
    ) -> None:
        """Create and sign a new certificate, store the chain to 'path'"""
        new_cert, new_key = self.issue_new_certificate(common_name, validity, key_size)
        _save_cert_chain(path, [new_cert, self.certificate], new_key)


def cert_dir(site_root_dir: Path) -> Path:
    return site_root_dir / "etc" / "ssl"


def root_cert_path(ca_dir: Path) -> Path:
    return ca_dir / "ca.pem"


def write_cert_store(source_dir: Path, store_path: Path) -> None:
    """Extract certificate part out of PEM files and concat
    to single cert store file."""
    pem_certs = (
        x509.load_pem_x509_certificate(pem_path.read_bytes()).public_bytes(Encoding.PEM)
        for pem_path in source_dir.glob("*.pem")
    )
    store_path.write_bytes(b"".join(pem_certs))


def _save_cert_chain(
    path_pem: Path,
    certificate_chain: Iterable[Certificate],
    key: PrivateKey,
) -> None:
    path_pem.parent.mkdir(mode=0o770, parents=True, exist_ok=True)
    with path_pem.open(mode="wb") as f:
        f.write(key.dump_pem(password=None).bytes)
        for cert in certificate_chain:
            f.write(cert.dump_pem().bytes)
    path_pem.chmod(mode=0o660)


class RemoteSiteCertsStore:
    # TODO: don't expose cryptography x509.Certificate in interface

    def __init__(self, path: Path) -> None:
        self.path: Final = path

    def save(self, site_id: SiteId, cert: x509.Certificate) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        self._make_file_name(site_id).write_bytes(Certificate(cert).dump_pem().bytes)

    def load(self, site_id: SiteId) -> x509.Certificate:
        return x509.load_pem_x509_certificate(self._make_file_name(site_id).read_bytes())

    def _make_file_name(self, site_id: SiteId) -> Path:
        return self.path / f"{site_id}.pem"


@dataclass
class CertManagementEvent(SecurityEvent):
    """Indicates a certificate has been added or removed"""

    ComponentType = Literal["saml", "agent controller", "backup encryption keys", "agent bakery"]

    def __init__(
        self,
        *,
        event: Literal["certificate created", "certificate removed", "certificate uploaded"],
        component: CertManagementEvent.ComponentType,
        actor: UserId | str | None,
        cert: Certificate | None,
    ) -> None:
        details = {
            "component": component,
            "actor": str(actor or "unknown user"),
        }
        if cert is not None:
            details |= {
                "issuer": str(cert.issuer.common_name or "none"),
                "subject": str(cert.subject.common_name or "none"),
                "not_valid_before": str(cert.not_valid_before.isoformat()),
                "not_valid_after": str(cert.not_valid_after.isoformat()),
                "fingerprint": cert.fingerprint(HashAlgorithm.Sha256).hex(sep=":").upper(),
            }
        super().__init__(
            event,
            details,
            SecurityEvent.Domain.cert_management,
        )
