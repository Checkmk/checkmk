#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from pathlib import Path

from dateutil.relativedelta import relativedelta

from livestatus import SiteConfiguration, SiteId

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site

from cmk.utils import paths
from cmk.utils.certs import save_single_cert

from cmk.gui.http import request as _request
from cmk.gui.i18n import _
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation

from cmk.crypto.certificate import (
    Certificate,
    CertificatePEM,
    CertificateWithPrivateKey,
    PersistedCertificateWithPrivateKey,
)
from cmk.messaging import (
    BrokerCertificates,
    ca_key_file,
    cacert_file,
    multisite_ca_key_file,
    multisite_cacert_file,
    multisite_cert_file,
    multisite_key_file,
    site_cert_file,
    site_key_file,
)


def create_broker_certs(
    cert_path: Path, key_path: Path, site_id: SiteId, ca: CertificateWithPrivateKey
) -> CertificateWithPrivateKey:
    """
    Create a new certificate for the broker of a site.
    Just store the certificate and not the private key.
    """

    bundle = ca.issue_new_certificate(
        common_name=site_id,
        organization=f"Checkmk Site {omd_site()}",
        expiry=relativedelta(years=2),
        key_size=4096,
    )

    save_single_cert(cert_path, bundle.certificate)

    return bundle


def load_or_create_broker_central_certs() -> PersistedCertificateWithPrivateKey:
    """
    Load, if present, or create a new certificate authority and certificate
    with private key for the central-site broker.
    """

    key_path = multisite_ca_key_file(paths.omd_root)
    cert_path = multisite_cacert_file(paths.omd_root)

    if key_path.exists() and cert_path.exists():
        return PersistedCertificateWithPrivateKey.read_files(cert_path, key_path)

    ca = CertificateWithPrivateKey.generate_self_signed(
        common_name="Message broker CA",
        organization=f"Checkmk Site {omd_site()}",
        expiry=relativedelta(years=5),
        key_size=4096,
        is_ca=True,
    )

    # be sure the folder are created
    cert_path.parent.mkdir(parents=True, exist_ok=True)

    # saves ca to etc/rabbitmq/ssl/multisite
    PersistedCertificateWithPrivateKey.persist(ca, cert_path, key_path)

    # saves certs to etc/rabbitmq/ssl/multisite
    bundle = create_broker_certs(
        multisite_cert_file(paths.omd_root, omd_site()),
        multisite_key_file(paths.omd_root, omd_site()),
        omd_site(),
        ca,
    )

    # saves certs to etc/rabbitmq/ssl/
    PersistedCertificateWithPrivateKey.persist(
        bundle, site_cert_file(paths.omd_root), site_key_file(paths.omd_root)
    )
    # saves ca to etc/rabbitmq/ssl
    return PersistedCertificateWithPrivateKey.persist(
        ca, cacert_file(paths.omd_root), ca_key_file(paths.omd_root)
    )


def broker_certs_created(site_id: SiteId) -> bool:
    return multisite_cert_file(paths.omd_root, site_id).exists()


def create_remote_broker_certs(
    central_site_ca: CertificateWithPrivateKey, site_id: SiteId, site: SiteConfiguration
) -> BrokerCertificates:
    """
    Create a new certificate with private key for the broker of a remote site.
    """

    cert_key = create_broker_certs(
        multisite_cert_file(paths.omd_root, site_id),
        multisite_key_file(paths.omd_root, site_id),
        site_id,
        central_site_ca,
    )
    return BrokerCertificates(
        key=cert_key[1].dump_pem(None).bytes,
        cert=cert_key[0].dump_pem().bytes,
        central_ca=central_site_ca.certificate.dump_pem().bytes,
    )


def sync_remote_broker_certs(
    site: SiteConfiguration, broker_certificates: BrokerCertificates
) -> None:
    """
    Send the broker certificates to the remote site for storage.
    """

    do_remote_automation(
        site,
        "store-broker-certs",
        [("certificates", broker_certificates.model_dump_json())],
        timeout=60,
    )


class AutomationStoreBrokerCertificates(AutomationCommand[BrokerCertificates]):
    def command_name(self) -> str:
        return "store-broker-certs"

    def get_request(self) -> BrokerCertificates:
        req = _request.get_str_input_mandatory("certificates")
        return BrokerCertificates.model_validate_json(req)

    def execute(self, api_request: BrokerCertificates) -> bool:
        try:
            ca_bytes = api_request.central_ca
            if api_request.customer_ca:
                ca_bytes += api_request.customer_ca
                ca = Certificate.load_pem(CertificatePEM(api_request.customer_ca))
            else:
                ca = Certificate.load_pem(CertificatePEM(api_request.central_ca))
            Certificate.load_pem(CertificatePEM(api_request.cert)).verify_is_signed_by(ca)

            store.save_bytes_to_file(cacert_file(paths.omd_root), ca_bytes)
            store.save_bytes_to_file(site_cert_file(paths.omd_root), api_request.cert)
            store.save_bytes_to_file(site_key_file(paths.omd_root), api_request.key)
        except Exception:
            raise MKGeneralException(
                _("Failed to save broker certificates: %s") % traceback.format_exc()
            )

        return True
