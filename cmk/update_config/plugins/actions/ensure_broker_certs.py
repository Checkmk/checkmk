#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Ensure the message broker certificates are created"""

from logging import Logger
from pathlib import Path

from cmk.ccc.site import omd_site

from cmk.utils.certs import MessagingTrustedCAs, SiteBrokerCA, SiteBrokerCertificate
from cmk.utils.paths import omd_root

from cmk import messaging
from cmk.update_config.registry import update_action_registry, UpdateAction


def initialize_message_broker_certs(root: Path, site_name: str, logger: Logger) -> None:
    """Initialize the CA and create the certificate for use with the message broker.
    These might be replaced by the config sync later.

    For sites created with Checkmk 2.4 or later this is done in a post-create hook.
    Compare `bin/message-broker-certs`.
    """
    ca = SiteBrokerCA(messaging.cacert_file(root), messaging.ca_key_file(root))
    site_broker_ca = SiteBrokerCertificate(
        messaging.site_cert_file(root), messaging.site_key_file(root)
    )
    # for a remote site the ca might not be there, that's fine: The central site signs the cert.
    if site_broker_ca.key_path.exists() and site_broker_ca.cert_path.exists():
        logger.info("Certificate found.")
        return

    ca_cert_bundle = ca.create_and_persist(site_name)
    MessagingTrustedCAs(messaging.trusted_cas_file(root)).write(
        ca_cert_bundle.certificate_path.read_bytes()
    )
    site_broker_ca.persist(site_broker_ca.create_bundle(site_name, ca_cert_bundle))


class EnsureBrokerCerts(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        initialize_message_broker_certs(omd_root, omd_site(), logger)


update_action_registry.register(
    EnsureBrokerCerts(
        name="ensure_message_broker_certs",
        title="Ensure message broker certs are ready",
        sort_index=255,  # Does not matter
    )
)
