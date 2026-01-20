#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import override

from dateutil.relativedelta import relativedelta

import cmk.utils.paths
from cmk.ccc.site import omd_site, SiteId
from cmk.gui.watolib.config_domains import ConfigDomainSiteCertificate
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.certs import (
    cert_dir,
    CertManagementEvent,
    SiteCA,
)
from cmk.utils.log.security_event import log_security_event


class UpdateSiteCertificate(UpdateAction):
    """
    Rotate central site certificate (ensuring they contain AKI).
    """

    @override
    def __call__(self, logger: Logger) -> None:
        try:
            if self._certificates_already_updated():
                logger.info("Site certificate already updated, skipping")
                return

            self.rotate_site_certificate(
                omd_root=cmk.utils.paths.omd_root,
                site_id=omd_site(),
            )
        except Exception as e:
            logger.error(f"Failed to update the Site certificate: {e}")

    def _certificates_already_updated(self) -> bool:
        try:
            site_id = omd_site()
            omd_root = cmk.utils.paths.omd_root
            certificate_directory = cert_dir(omd_root)
            site_ca = SiteCA.load(certificate_directory)
            site_cert = site_ca.load_site_certificate(certificate_directory, site_id)
            if site_cert is None:
                return False

        except FileNotFoundError:
            return False

        return site_cert.certificate.has_authority_key_identifier()

    @staticmethod
    def rotate_site_certificate(
        omd_root: Path,
        site_id: SiteId,
    ) -> None:
        sans = (
            ConfigDomainSiteCertificate()
            .load_full_config()
            .get("site_subject_alternative_names", [])
        )

        certificate_directory = cert_dir(omd_root)
        site_ca = SiteCA.load(certificate_directory)
        site_ca.create_site_certificate(
            site_id=site_id,
            additional_sans=sans,
            expiry=relativedelta(days=730),
            key_size=4096,
        )

        site_cert = site_ca.load_site_certificate(certificate_directory, site_id)
        if not site_cert:
            raise RuntimeError(f"Failed to load site certificate for site {site_id}")

        log_security_event(
            CertManagementEvent(
                event="certificate rotated",
                component="site certificate",
                actor="cmk-update-config",
                cert=site_cert.certificate,
            )
        )


update_action_registry.register(
    UpdateSiteCertificate(
        name="update-site-certificate",
        title="Update Site Certificate",
        sort_index=100,  # don't care
        expiry_version=ExpiryVersion.CMK_300,
        continue_on_failure=True,
    )
)
