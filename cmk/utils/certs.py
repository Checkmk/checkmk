#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, Self

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding, load_pem_private_key
from dateutil.relativedelta import relativedelta

from livestatus import SiteId

from cmk.ccc.site import omd_site

from cmk.utils.log.security_event import SecurityEvent
from cmk.utils.user import UserId

from cmk import messaging
from cmk.crypto.certificate import (
    Certificate,
    CertificatePEM,
    CertificateWithPrivateKey,
    PersistedCertificateWithPrivateKey,
)
from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.keys import is_supported_private_key_type, PrivateKey


class _CNTemplate:
    """Template used to create the certs CN containing the sites name"""

    def __init__(self, template: str) -> None:
        self._temp = template
        self._match = re.compile("CN=" + template % "([^=+,]*)").search

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

    def issue_and_store_certificate(
        self,
        path: Path,
        common_name: str,
        validity: relativedelta = _DEFAULT_VALIDITY,
        key_size: int = _DEFAULT_KEY_SIZE,
    ) -> None:
        """Create and sign a new certificate, store the chain to 'path'"""
        new_cert, new_key = self.issue_new_certificate(
            common_name=common_name,
            organization=f"Checkmk Site {omd_site()}",
            subject_alt_dns_names=[common_name],
            expiry=validity,
            key_size=key_size,
        )
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
    _prepare_certfile_path(path_pem)
    with path_pem.open(mode="wb") as f:
        f.write(key.dump_pem(password=None).bytes)
        for cert in certificate_chain:
            f.write(cert.dump_pem().bytes)
    _set_certfile_permissions(path_pem)


def save_single_cert(
    path_pem: Path,
    cert: Certificate,
) -> None:
    _prepare_certfile_path(path_pem)
    with path_pem.open(mode="wb") as f:
        f.write(cert.dump_pem().bytes)
    _set_certfile_permissions(path_pem)


def save_single_key(
    path_pem: Path,
    key: PrivateKey,
) -> None:
    _prepare_certfile_path(path_pem)
    with path_pem.open(mode="wb") as f:
        f.write(key.dump_pem(password=None).bytes)
    _set_certfile_permissions(path_pem)


def _prepare_certfile_path(
    path_pem: Path,
) -> None:
    path_pem.parent.mkdir(mode=0o770, parents=True, exist_ok=True)


def _set_certfile_permissions(
    path_pem: Path,
) -> None:
    path_pem.chmod(mode=0o660)


class RemoteSiteCertsStore:
    def __init__(self, path: Path) -> None:
        self.path: Final = path

    def save(self, site_id: SiteId, cert: Certificate) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        self._make_file_name(site_id).write_bytes(cert.dump_pem().bytes)

    def load(self, site_id: SiteId) -> Certificate:
        return Certificate.load_pem(CertificatePEM(self._make_file_name(site_id).read_bytes()))

    def _make_file_name(self, site_id: SiteId) -> Path:
        return self.path / f"{site_id}.pem"


@dataclass
class CertManagementEvent(SecurityEvent):
    """Indicates a certificate has been added or removed"""

    ComponentType = Literal[
        "saml",
        "agent controller",
        "backup encryption keys",
        "agent bakery",
        "trusted certificate authorities",
    ]

    def __init__(
        self,
        *,
        event: Literal[
            "certificate created",
            "certificate removed",
            "certificate uploaded",
            "certificate added",
        ],
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


class SiteBrokerCertificate:
    def __init__(self, bundle: CertificateWithPrivateKey) -> None:
        self.cert_bundle = bundle

    @classmethod
    def key_path(cls, omd_root: Path) -> Path:
        return messaging.site_key_file(omd_root)

    @classmethod
    def cert_path(cls, omd_root: Path) -> Path:
        return messaging.site_cert_file(omd_root)

    @classmethod
    def create(cls, site_name: str, omd_root: Path, issuer: CertificateWithPrivateKey) -> Self:
        """Have the site's certificate issued by the given CA.

        The certificate and key are not persisted to disk directly because this method is also used
        to create certificates for remote sites.
        """
        organization = f"Checkmk Site {site_name}"
        expires = relativedelta(years=2)
        is_ca = False
        key_size = 4096

        cert_bundle = issuer.issue_new_certificate(
            common_name=site_name,
            organization=organization,
            expiry=expires,
            key_size=key_size,
            is_ca=is_ca,
        )

        return cls(cert_bundle)

    def persist(self, omd_root: Path) -> None:
        cert_path = self.cert_path(omd_root)
        key_path = self.key_path(omd_root)

        cert_path.parent.mkdir(parents=True, exist_ok=True)
        PersistedCertificateWithPrivateKey.persist(self.cert_bundle, cert_path, key_path)

    @classmethod
    def persist_broker_certificates(
        cls,
        omd_root: Path,
        received: messaging.BrokerCertificates,
    ) -> None:
        """Persist the received certificates to disk."""
        cert_path = cls.cert_path(omd_root)

        ca = Certificate.load_pem(CertificatePEM(received.signing_ca))
        Certificate.load_pem(CertificatePEM(received.cert)).verify_is_signed_by(ca)

        cert_path.parent.mkdir(parents=True, exist_ok=True)

        MessagingTrustedCAs.write(omd_root, received.signing_ca + received.additionally_trusted_ca)
        cert_path.write_bytes(received.cert)


class SiteBrokerCA:
    def __init__(self, bundle: PersistedCertificateWithPrivateKey) -> None:
        self.cert_bundle = bundle

    @classmethod
    def key_path(cls, omd_root: Path) -> Path:
        return messaging.ca_key_file(omd_root)

    @classmethod
    def cert_path(cls, omd_root: Path) -> Path:
        return messaging.cacert_file(omd_root)

    @classmethod
    def create_and_persist(cls, site_name: str, omd_root: Path) -> Self:
        common_name = f"Site '{site_name}' broker CA"
        organization = f"Checkmk Site {site_name}"
        expires = relativedelta(years=5)
        key_size = 4096
        is_ca = True

        cert_path = cls.cert_path(omd_root)
        key_path = cls.key_path(omd_root)

        cert = CertificateWithPrivateKey.generate_self_signed(
            common_name=common_name,
            organization=organization,
            expiry=expires,
            key_size=key_size,
            is_ca=is_ca,
        )

        cert_path.parent.mkdir(parents=True, exist_ok=True)
        return cls(PersistedCertificateWithPrivateKey.persist(cert, cert_path, key_path))

    @classmethod
    def load(cls, omd_root: Path) -> Self:
        return cls(
            PersistedCertificateWithPrivateKey.read_files(
                cls.cert_path(omd_root),
                cls.key_path(omd_root),
            )
        )

    def write_trusted_cas_file(self, omd_root: Path) -> None:
        messaging.trusted_cas_file(omd_root).write_text(
            self.cert_bundle.certificate_path.read_text()
        )

    @classmethod
    def delete(cls, omd_root: Path) -> None:
        cls.cert_path(omd_root).unlink(missing_ok=True)
        cls.key_path(omd_root).unlink(missing_ok=True)


class CustomerBrokerCA:
    def __init__(self, bundle: PersistedCertificateWithPrivateKey) -> None:
        self.cert_bundle = bundle

    @classmethod
    def key_path(cls, omd_root: Path, customer: str) -> Path:
        return messaging.multisite_ca_key_file(omd_root, customer)

    @classmethod
    def cert_path(cls, omd_root: Path, customer: str) -> Path:
        return messaging.multisite_cacert_file(omd_root, customer)

    @classmethod
    def create_and_persist(cls, customer: str, site_name: str, omd_root: Path) -> Self:
        common_name = f"Message broker '{customer}' CA"
        organization = f"Checkmk Site {site_name}"
        expires = relativedelta(years=5)
        key_size = 4096
        is_ca = True

        cert_path = cls.cert_path(omd_root, customer)
        key_path = cls.key_path(omd_root, customer)

        cert = CertificateWithPrivateKey.generate_self_signed(
            common_name=common_name,
            organization=organization,
            expiry=expires,
            key_size=key_size,
            is_ca=is_ca,
        )

        cert_path.parent.mkdir(parents=True, exist_ok=True)
        return cls(PersistedCertificateWithPrivateKey.persist(cert, cert_path, key_path))

    @classmethod
    def load(cls, customer: str, omd_root: Path) -> Self:
        return cls(
            PersistedCertificateWithPrivateKey.read_files(
                cls.cert_path(omd_root, customer),
                cls.key_path(omd_root, customer),
            )
        )

    @classmethod
    def delete(cls, customer: str, omd_root: Path) -> None:
        cls.cert_path(omd_root, customer).unlink(missing_ok=True)
        cls.key_path(omd_root, customer).unlink(missing_ok=True)


class LocalBrokerCertificate:
    @classmethod
    def cert_path(cls, omd_root: Path, site_name: str) -> Path:
        return messaging.multisite_cert_file(omd_root, site_name)

    @classmethod
    def load(cls, site_name: str, omd_root: Path) -> Certificate:
        return Certificate.load_pem(CertificatePEM(cls.cert_path(omd_root, site_name).read_bytes()))

    @classmethod
    def write(cls, site_name: str, omd_root: Path, cert: bytes) -> None:
        save_single_cert(
            cls.cert_path(omd_root, site_name),
            Certificate.load_pem(CertificatePEM(cert)),
        )

    @classmethod
    def exists(cls, site_name: str, omd_root: Path) -> bool:
        return cls.cert_path(omd_root, site_name).exists()


class MessagingTrustedCAs:
    @classmethod
    def path(cls, omd_root: Path) -> Path:
        return messaging.trusted_cas_file(omd_root)

    @classmethod
    def write(cls, omd_root: Path, certs: bytes) -> None:
        cls.path(omd_root).write_bytes(certs)

    @classmethod
    def update_trust_cme(cls, omd_root: Path) -> None:
        """Add all customer CAs to the trusted CAs file. Only relevant in a multisite setup."""
        trusted_cas = [SiteBrokerCA.cert_path(omd_root).read_bytes()]
        for path in messaging.all_cme_cacert_files(omd_root):
            try:
                trusted_cas.append(path.read_bytes())
            except FileNotFoundError:
                pass

        cls.write(omd_root, b"".join(trusted_cas))
