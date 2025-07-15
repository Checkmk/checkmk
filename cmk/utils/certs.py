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

from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId

from cmk.utils.log.security_event import SecurityEvent

from cmk.crypto.certificate import (
    Certificate,
    CertificatePEM,
    CertificateWithPrivateKey,
    PersistedCertificateWithPrivateKey,
)
from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.keys import is_supported_private_key_type, PrivateKey
from cmk.crypto.x509 import SAN, SubjectAlternativeNames


class _CNTemplate:
    """Template used to create the certs CN containing the sites name"""

    def __init__(self, template: str) -> None:
        self._temp = template
        self._match = re.compile("CN=" + template % "([^=+,]*)").search

    def format(self, site: SiteId | str) -> str:
        return self._temp % site

    def extract_site(self, rfc4514_string: str) -> SiteId | None:
        return None if (m := self._match(rfc4514_string)) is None else SiteId(m.group(1))


# TODO: remove the use of this in watolib/config_domains, then it can go away
CN_TEMPLATE = _CNTemplate("Site '%s' local CA")


class RootCA(CertificateWithPrivateKey):
    """A generic certificate authority for all our CA needs.

    This class should be replaced by individual classes for each use case, like the SiteCA and
    message-broker classes below.
    """

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
        validity: relativedelta = relativedelta(years=10),
        key_size: int = 4096,
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


def cert_dir(site_root_dir: Path) -> Path:
    # TODO: some places in the code ask this function, some use cmk.utils.paths...
    return site_root_dir / "etc" / "ssl"


def agent_root_ca_path(site_root_dir: Path) -> Path:
    # TODO: some places in the code ask this function, some use cmk.utils.paths...
    return cert_dir(site_root_dir) / "agents" / "ca.pem"


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


def _prepare_certfile_path(
    path_pem: Path,
) -> None:
    path_pem.parent.mkdir(mode=0o770, parents=True, exist_ok=True)


def _set_certfile_permissions(
    path_pem: Path,
) -> None:
    path_pem.chmod(mode=0o660)


class SiteCA:
    """Management of the site local CA and certificates issued by it"""

    def __init__(self, certificate_directory: Path, root_ca: CertificateWithPrivateKey) -> None:
        """Initialize SiteCA with a certificate directory and root CA.

        You should probably use `load_or_create` or `load` instead.
        """
        self._cert_dir = certificate_directory
        self.root_ca = root_ca

    @classmethod
    def load_or_create(
        cls,
        site_id: str,
        certificate_directory: Path,
        expiry: relativedelta = relativedelta(years=10),
        key_size: int = 4096,
    ) -> SiteCA:
        """Load an existing CA for the given site or create a new one if it does not exist."""
        try:
            return cls.load(certificate_directory)

        except FileNotFoundError:
            return cls(
                certificate_directory,
                cls._create_root_certificate(
                    certificate_directory,
                    site_id,
                    CN_TEMPLATE.format(site=site_id),
                    expiry,
                    key_size,
                ),
            )

    @classmethod
    def load(cls, certificate_directory: Path) -> SiteCA:
        """Load an existing CA for the given site from the given directory."""
        return cls(
            certificate_directory,
            CertificateWithPrivateKey.load_combined_file_content(
                SiteCA._ca_file(certificate_directory).read_text(), passphrase=None
            ),
        )

    @property
    def root_ca_path(self) -> Path:
        return self._ca_file(self._cert_dir)

    def _site_certificate_path(self, site_id: str) -> Path:
        return (self._cert_dir / "sites" / site_id).with_suffix(".pem")

    def site_certificate_exists(self, site_id: str) -> bool:
        return self._site_certificate_path(site_id).exists()

    def create_site_certificate(
        self,
        site_id: str,
        expiry: relativedelta = relativedelta(years=10),
        key_size: int = 4096,
    ) -> None:
        """Creates the key / certificate for the given Checkmk site"""
        new_cert, new_key = self.root_ca.issue_new_certificate(
            common_name=site_id,
            organization=f"Checkmk Site {site_id}",
            subject_alternative_names=SubjectAlternativeNames([SAN.dns_name(site_id)]),
            expiry=expiry,
            key_size=key_size,
        )

        self._save_combined_pem(
            target_file=self._site_certificate_path(site_id),
            certificate=new_cert,
            private_key=new_key,
            issuer=self.root_ca.certificate,
        )

    @staticmethod
    def _ca_file(certificate_directory: Path) -> Path:
        return certificate_directory / "ca.pem"

    @staticmethod
    def _save_combined_pem(
        target_file: Path,
        certificate: Certificate,
        private_key: PrivateKey,
        issuer: Certificate | None,
    ) -> None:
        target_file.parent.mkdir(mode=0o770, parents=True, exist_ok=True)

        with target_file.open(mode="wb") as f:
            f.write(private_key.dump_pem(password=None).bytes)
            f.write(certificate.dump_pem().bytes)
            if issuer is not None:
                f.write(issuer.dump_pem().bytes)

        target_file.chmod(mode=0o660)

    @staticmethod
    def _create_root_certificate(
        cert_dir: Path,
        site_id: str,
        common_name: str,
        expiry: relativedelta,
        key_size: int,
    ) -> CertificateWithPrivateKey:
        ca = CertificateWithPrivateKey.generate_self_signed(
            common_name=common_name,
            organization=f"Checkmk Site {site_id}",
            expiry=expiry,
            key_size=key_size,
            is_ca=True,
        )

        SiteCA._save_combined_pem(
            target_file=SiteCA._ca_file(cert_dir),
            certificate=ca.certificate,
            private_key=ca.private_key,
            issuer=None,
        )

        return ca


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
    def __init__(self, cert_path: Path, key_path: Path) -> None:
        self.cert_path: Final = cert_path
        self.key_path: Final = key_path

    @classmethod
    def create_bundle(
        cls, site_name: str, issuer: CertificateWithPrivateKey
    ) -> CertificateWithPrivateKey:
        """Have the site's certificate issued by the given CA.

        The certificate and key are not persisted to disk directly because this method is also used
        to create certificates for remote sites.
        """
        organization = f"Checkmk Site {site_name}"
        expires = relativedelta(years=2)
        is_ca = False
        key_size = 4096

        return issuer.issue_new_certificate(
            common_name=site_name,
            organization=organization,
            expiry=expires,
            key_size=key_size,
            is_ca=is_ca,
        )

    def persist(self, cert_bundle: CertificateWithPrivateKey) -> None:
        self.cert_path.parent.mkdir(parents=True, exist_ok=True)
        PersistedCertificateWithPrivateKey.persist(cert_bundle, self.cert_path, self.key_path)

    def persist_broker_certificates(
        self,
        signing_ca: bytes,
        cert: bytes,
        additionally_trusted_ca: bytes,
        trusted_cas_store: MessagingTrustedCAs,
    ) -> None:
        """Persist the received certificates to disk."""
        ca = Certificate.load_pem(CertificatePEM(signing_ca))
        Certificate.load_pem(CertificatePEM(cert)).verify_is_signed_by(ca)

        self.cert_path.parent.mkdir(parents=True, exist_ok=True)

        trusted_cas_store.write(signing_ca + additionally_trusted_ca)
        self.cert_path.write_bytes(cert)


class SiteBrokerCA:
    def __init__(self, cert_path: Path, key_path: Path) -> None:
        self.cert_path: Final = cert_path
        self.key_path: Final = key_path

    def create_and_persist(self, site_name: str) -> PersistedCertificateWithPrivateKey:
        common_name = f"Site '{site_name}' broker CA"
        organization = f"Checkmk Site {site_name}"
        expires = relativedelta(years=5)
        key_size = 4096
        is_ca = True

        cert = CertificateWithPrivateKey.generate_self_signed(
            common_name=common_name,
            organization=organization,
            expiry=expires,
            key_size=key_size,
            is_ca=is_ca,
        )

        self.cert_path.parent.mkdir(parents=True, exist_ok=True)
        return PersistedCertificateWithPrivateKey.persist(cert, self.cert_path, self.key_path)

    def load(self) -> PersistedCertificateWithPrivateKey:
        return PersistedCertificateWithPrivateKey.read_files(self.cert_path, self.key_path)

    def delete(self) -> None:
        self.cert_path.unlink(missing_ok=True)
        self.key_path.unlink(missing_ok=True)


class CustomerBrokerCA:
    def __init__(self, cert_path: Path, key_path: Path) -> None:
        self.cert_path: Final = cert_path
        self.key_path: Final = key_path

    def create_and_persist(
        self, customer: str, site_name: str
    ) -> PersistedCertificateWithPrivateKey:
        common_name = f"Message broker '{customer}' CA"
        organization = f"Checkmk Site {site_name}"
        expires = relativedelta(years=5)
        key_size = 4096
        is_ca = True

        cert = CertificateWithPrivateKey.generate_self_signed(
            common_name=common_name,
            organization=organization,
            expiry=expires,
            key_size=key_size,
            is_ca=is_ca,
        )

        self.cert_path.parent.mkdir(parents=True, exist_ok=True)
        return PersistedCertificateWithPrivateKey.persist(cert, self.cert_path, self.key_path)

    def load(self) -> PersistedCertificateWithPrivateKey:
        return PersistedCertificateWithPrivateKey.read_files(self.cert_path, self.key_path)

    def delete(self) -> None:
        self.cert_path.unlink(missing_ok=True)
        self.key_path.unlink(missing_ok=True)


class LocalBrokerCertificate:
    def __init__(self, path: Path) -> None:
        self.cert_path: Final = path

    def load(self) -> Certificate:
        return Certificate.load_pem(CertificatePEM(self.cert_path.read_bytes()))

    def write(self, cert: bytes) -> None:
        _prepare_certfile_path(self.cert_path)

        # TODO: Do we load and dump the certificate for validation here, or can we skip that?
        with self.cert_path.open(mode="wb") as f:
            f.write(Certificate.load_pem(CertificatePEM(cert)).dump_pem().bytes)

        _set_certfile_permissions(self.cert_path)

    def exists(self) -> bool:
        return self.cert_path.exists()


class MessagingTrustedCAs:
    def __init__(self, path: Path) -> None:
        self.path: Final = path

    def write(self, certs: bytes) -> None:
        self.path.write_bytes(certs)

    def update_trust_cme(self, update_from: Iterable[Path]) -> None:
        """Add all customer CAs to the trusted CAs file. Only relevant in a multisite setup."""
        trusted_cas = []
        for path in update_from:
            try:
                trusted_cas.append(path.read_bytes())
            except FileNotFoundError:
                pass

        self.write(b"".join(trusted_cas))
