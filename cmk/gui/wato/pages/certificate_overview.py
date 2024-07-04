#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for managing users and contacts"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date

from cmk.gui.i18n import _
from cmk.gui.table import table_element
from cmk.gui.type_defs import PermissionName
from cmk.gui.watolib.mode import ModeRegistry, WatoMode


@dataclass
class CertificateView:
    subject_name: str
    issuer_name: str
    creation: date
    expiration: date
    fingerprint: str
    key_type_length: str
    stored_location: str
    purpose: str

    def get_fields(self) -> dict[str, str]:
        """Get title and value of fields."""
        return {
            _("Subject Name"): self.subject_name,
            _("Issuer Name"): self.issuer_name,
            _("Creation Date"): self.creation.isoformat(),
            _("Expiration Date"): self.expiration.isoformat(),
            _("Fingerprint"): self.fingerprint,
            _("Key Type and Length"): self.key_type_length,
            _("Stored Location"): self.stored_location,
            _("Purpose"): self.purpose,
        }


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeCertificateOverview)


# Todo: This page is not complete yet. It is just a placeholder for the certificate overview.
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
            CertificateView(
                subject_name="site",
                issuer_name="Heute",
                creation=date(2023, 1, 1),
                expiration=date(2023, 12, 30),
                fingerprint="00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF",
                key_type_length="RSA 2048 bits",
                stored_location="etc/ssl/certs",
                purpose="Monitoring",
            ),
            CertificateView(
                subject_name="agent",
                issuer_name="Heute",
                creation=date(2023, 1, 1),
                expiration=date(2023, 12, 30),
                fingerprint="00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF",
                key_type_length="RSA 2048 bits",
                stored_location="etc/ssl/certs/agent.pem",
                purpose="Agent communication",
            ),
        ]
