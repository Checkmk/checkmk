#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for showing the certificates."""

# mypy: disable-error-code="type-arg"

import hashlib
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from cmk.crypto import MKCryptoException
from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.x509 import X509Name
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.cert_info import cert_info_registry, CertificateInfo
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import ContentDispositionType, request, response
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import Page, PageContext, PageEndpoint, PageRegistry
from cmk.gui.table import table_element
from cmk.gui.type_defs import IconNames, PermissionName, StaticIcon
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import DocReference, makeuri_contextless
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.messaging import get_cert_info
from cmk.utils.paths import (
    agent_cas_dir,
    relay_cas_dir,
    root_cert_file,
    site_cert_file,
)


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
            _("Common name (subject)"): self.subject.common_name or _("None"),
            _("Common name (issuer)"): self.issuer.common_name or _("None"),
            _("Creation date"): self.creation.isoformat(),
            _("Expiration date"): self.expiration.isoformat(),
            _("Fingerprint"): HTMLWriter.render_span(self.fingerprint[:17], title=self.fingerprint),
            _("Key type and length"): self.key_type_length,
            _("Stored location"): str(self.stored_location),
            _("Purpose"): self.purpose or _("None"),
            _("Download"): html.render_icon_button(
                url=makeuri_contextless(
                    request,
                    [("cert", certificate_id(self.stored_location))],
                    filename="download_certificate.py",
                ),
                title=_("Download"),
                icon=StaticIcon(IconNames.download),
            ),
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


def registered_certificates() -> dict[Path, str]:
    """All certificates of the overview page, by path. This is the download allow list."""
    return {
        path: purpose
        for topic in cert_info_registry
        for path, purpose in cert_info_registry[topic].get_certs().items()
        if path.exists()
    }


def certificate_id(path: Path) -> str:
    """A stable, opaque handle for a certificate.

    The download link must not carry the certificate's path: that would expose the sites
    file system layout, and the file names alone are not unique (several CAs are stored
    as "ca.pem").
    """
    return hashlib.sha256(str(path).encode()).hexdigest()


class PageDownloadCertificate(Page):
    """Serve a certificate as a same origin download.

    Inlining the PEM as a ``data:`` URI does not work in all browsers: Firefox refuses
    to navigate the Setup iframe to a ``data:`` URI, and the sites CSP does not allow it
    either (CMK-38956).
    """

    def page(self, ctx: PageContext) -> None:
        # IMHO we don't need to check permissions here. The public keys should not be confidential
        # and most of the certificates/CAs could be retrieved in a TLS handshake anyway.
        cert_id = ctx.request.get_str_input_mandatory("cert")
        by_id = {certificate_id(path): path for path in registered_certificates()}
        if (path := by_id.get(cert_id)) is None:
            raise MKUserError("cert", _("Unknown certificate."))

        try:
            cert = Certificate.load_pem(CertificatePEM(path.read_bytes()))
        except (OSError, MKCryptoException):
            # the certificate may have been rotated or removed since we listed it
            raise MKUserError("cert", _("Could not read the certificate."))

        response.set_content_type("application/x-pem-file")
        response.set_content_disposition(ContentDispositionType.ATTACHMENT, path.name)
        response.set_data(cert.dump_pem().bytes)


def register(mode_registry: ModeRegistry, page_registry: PageRegistry) -> None:
    mode_registry.register(ModeCertificateOverview)
    page_registry.register(PageEndpoint("download_certificate", PageDownloadCertificate()))
    cert_info_registry.register(
        CertificateInfo(
            "builtin",
            lambda: {
                root_cert_file: _("Signing the site certificate"),
                agent_cas_dir / "ca.pem": _("Signing agents' client certificates"),
                relay_cas_dir / "ca.pem": _("Signing Relay client certificates"),
                site_cert_file: _("The site certificate"),
            },
        )
    )
    cert_info_registry.register(
        CertificateInfo(
            "messaging",
            get_cert_info,
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

    def page(self, config: Config) -> None:
        html.div(
            HTML.without_escaping(
                _(
                    "This page provides a comprehensive overview of the certificates Checkmk uses internally. "
                    "Trusted CAs for TLS are managed in the <a href='%s'>settings</a>."
                )
                % "wato.py?mode=edit_configvar&varname=trusted_certificate_authorities"
            ),
            class_="info",
        )
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
            for path, purpose in registered_certificates().items()
        ]

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Global"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Trusted certificate authorities for SSL"),
                                    icon_name=StaticIcon(IconNames.configuration),
                                    item=make_simple_link(
                                        "wato.py?mode=edit_configvar&varname=trusted_certificate_authorities"
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )
        menu.add_doc_reference(_("Certificate overview in Checkmk"), DocReference.CERTIFICATES)
        return menu
