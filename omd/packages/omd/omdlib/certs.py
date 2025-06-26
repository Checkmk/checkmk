#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Management of the site local CA and certificates issued by it"""

from pathlib import Path

from dateutil.relativedelta import relativedelta

from cmk.utils.certs import CN_TEMPLATE

from cmk.crypto.certificate import Certificate, CertificateWithPrivateKey
from cmk.crypto.keys import PrivateKey
from cmk.crypto.x509 import SAN, SubjectAlternativeNames


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
    ) -> "SiteCA":
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
    def load(cls, certificate_directory: Path) -> "SiteCA":
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
