#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for showing the certificates."""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from cmk.utils.paths import (
    agent_cas_dir,
    root_cert_file,
    site_cert_file,
)

from cmk.gui.cert_info import cert_info_registry, CertificateInfo
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.table import table_element
from cmk.gui.type_defs import PermissionName
from cmk.gui.utils.html import HTML
from cmk.gui.watolib.mode import ModeRegistry, WatoMode

from cmk.crypto.certificate import Certificate, CertificatePEM, X509Name
from cmk.crypto.hash import HashAlgorithm


@dataclass
class CertificateView:
    """Represents a certificate in the certificate overview."""

    subject: X509Name
    issuer: X509Name
    creation: date
    expiration: date
    fingerprint: str
    key_type_length: str
    stored_location: Path
    purpose: str | None

    def get_fields(self) -> dict[str, str | HTML]:
        """Get title and value of fields."""
        return {
            _("Subject Name"): self.subject.common_name or _("None"),
            _("Issuer Name"): self.issuer.common_name or _("None"),
            _("Creation Date"): self.creation.isoformat(),
            _("Expiration Date"): self.expiration.isoformat(),
            _("Fingerprint"): HTMLWriter.render_span(self.fingerprint[:17], title=self.fingerprint),
            _("Key Type and Length"): self.key_type_length,
            _("Stored Location"): str(self.stored_location),
            _("Purpose"): self.purpose or _("None"),
        }

    @classmethod
    def load(cls, path: Path, purpose: str | None = None) -> "CertificateView":
        cert = Certificate.load_pem(CertificatePEM(path.read_bytes()))
        return cls(
            subject=cert.subject,
            issuer=cert.issuer,
            creation=cert.not_valid_before.date(),
            expiration=cert.not_valid_after.date(),
            fingerprint=cert.fingerprint(HashAlgorithm.Sha256).hex(sep=":").upper(),
            key_type_length=cert.public_key.show_type(),
            stored_location=path,
            purpose=purpose,
        )


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeCertificateOverview)
    cert_info_registry.register(
        CertificateInfo(
            "builtin",
            lambda: {
                root_cert_file: _("Signing the site certificate"),
                agent_cas_dir / "ca.pem": _("Signing agents' client certificates"),
                site_cert_file: _("The site certificate"),
            },
        )
    )


class ModeCertificateOverview(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "certificate_overview"

    def title(self) -> str:
        return _("Certificate overview")

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        # Todo: should change to "certificate.view" once we have a permission for this
        return []

    def page(self) -> None:
        certificates = self._load_certificates()
        self._render_table(certificates)

    def _render_table(self, certificates: list[CertificateView]) -> None:
        with table_element(sortable=True, searchable=True) as table:
            for cert in certificates:
                table.row()
                for title, value in cert.get_fields().items():
                    table.cell(title, value)

    def _load_certificates(self) -> list[CertificateView]:
        return [
            CertificateView.load(path, purpose)
            for topic in cert_info_registry
            for path, purpose in cert_info_registry[topic].get_certs().items()
            if path.exists()
        ]
