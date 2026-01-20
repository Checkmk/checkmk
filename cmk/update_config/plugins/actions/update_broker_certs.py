#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk import messaging
from cmk.ccc.site import omd_site
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.watolib.broker_certificates import clean_remote_sites_certs
from cmk.gui.watolib.sites import site_management_registry
from cmk.message_broker_certs import initialize_message_broker_certs
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.certs import SiteBrokerCertificate
from cmk.utils.paths import omd_root


class UpdateBrokerCerts(UpdateAction):
    """
    1. Rotate/re-issue central site certificates (ensuring they contain AKI).
    2. Empty the remote site certificate folder to force certificate creation and sync
       on next login
    This ensures all remote sites receive certificates with the AKI.
    """

    @override
    def __call__(self, logger: Logger) -> None:
        try:
            if self._is_remote_site(logger):
                logger.info("Broker certificate update skipped on remote site")
                return

            if self._certificates_already_updated():
                logger.info("Broker certificates already updated, skipping")
                return

            initialize_message_broker_certs(omd_root, omd_site())
            clean_remote_sites_certs(kept_sites=[])
        except Exception as e:
            logger.error(
                f"Failed to update Broker certificates: {e}. Please re-create them manually."
            )

    def _is_remote_site(self, logger: Logger) -> bool:
        site_mgmt = site_management_registry["site_management"]
        all_sites = site_mgmt.load_sites()
        return is_distributed_setup_remote_site(all_sites)

    def _certificates_already_updated(self) -> bool:
        try:
            cert = SiteBrokerCertificate(
                messaging.site_cert_file(omd_root), messaging.site_key_file(omd_root)
            ).load()
        except FileNotFoundError:
            return False

        return cert.certificate.has_authority_key_identifier()


update_action_registry.register(
    UpdateBrokerCerts(
        name="update-broker-certs",
        title="Update Broker Certificates",
        sort_index=1,  # Must be executed before initialize_site_configuration (which empties distributed_wato.mk)
        # for 2.6 also re-enable strict verification in packages/cmk-messaging/cmk/messaging/_config.py::_make_ssl_context
        expiry_version=ExpiryVersion.CMK_300,
        continue_on_failure=True,
    )
)
