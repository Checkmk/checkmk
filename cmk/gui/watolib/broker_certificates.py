#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from pathlib import Path

from dateutil.relativedelta import relativedelta

from livestatus import SiteConfiguration, SiteId

from cmk.utils import paths
from cmk.utils.certs import RootCA, save_single_cert, save_single_key

from cmk.gui.http import request as _request
from cmk.gui.i18n import _
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site
from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.crypto.keys import PrivateKey
from cmk.messaging import (
    BrokerCertificates,
    cacert_file,
    cert_file,
    key_file,
    multisite_cacert_file,
    multisite_cert_file,
    multisite_key_file,
)


def site_cert(
    cert_path: Path, key_path: Path, site_id: SiteId, ca: RootCA
) -> tuple[Certificate, PrivateKey]:

    cert, key = ca.issue_new_certificate(
        common_name=site_id,
        organization=f"Checkmk Site {omd_site()}",
        expiry=relativedelta(years=2),
        key_size=4096,
    )

    save_single_cert(cert_path, cert)
    # just save private key for local site
    # no need to save locally here for remote sites
    # (will be done by the automation)
    if omd_site() == site_id:
        save_single_key(key_path, key)
    return cert, key


def _load_create_site_cert(site_id: SiteId, ca: RootCA) -> tuple[Certificate, PrivateKey]:
    cert_path = multisite_cert_file(paths.omd_root, site_id)
    key_path = multisite_key_file(paths.omd_root, site_id)
    return site_cert(cert_path, key_path, site_id, ca)


def generate_local_broker_ca() -> RootCA:
    return RootCA.load_or_create(
        multisite_cacert_file(paths.omd_root),
        "Message broker CA",
    )


def _cert_generated(site_id: SiteId) -> bool:
    return multisite_cert_file(paths.omd_root, site_id).exists()


def remote_broker_certificates(
    central_site_ca: RootCA, site_id: SiteId, site: SiteConfiguration
) -> BrokerCertificates | None:

    # no need to do anything if the public key is already present
    if _cert_generated(site_id):
        return None

    cert_key = _load_create_site_cert(site_id, central_site_ca)
    return BrokerCertificates(
        key=cert_key[1].dump_pem(None).bytes,
        cert=cert_key[0].dump_pem().bytes,
        central_ca=central_site_ca.certificate.dump_pem().bytes,
    )


def generate_remote_broker_certificate(
    central_site_ca: RootCA, site_id: SiteId, site: SiteConfiguration
) -> bool:

    if (broker_certificates := remote_broker_certificates(central_site_ca, site_id, site)) is None:
        return False

    res = do_remote_automation(
        site,
        "store-broker-certs",
        [("certificates", broker_certificates.model_dump_json())],
        timeout=60,
    )

    return res if isinstance(res, bool) else False


def dump_central_site_broker_certificates() -> None:
    central_ca = RootCA.load(multisite_cacert_file(paths.omd_root))

    if (site_certs := _load_create_site_cert(omd_site(), central_ca)) is not None:
        save_single_key(key_file(paths.omd_root), site_certs[1])
        save_single_cert(cert_file(paths.omd_root), site_certs[0])

    central_ca_certs = [
        central_ca.private_key.dump_pem(None).bytes,
        central_ca.certificate.dump_pem().bytes,
    ]

    store.save_bytes_to_file(cacert_file(paths.omd_root), b"".join(central_ca_certs))


class AutomationStoreBrokerCertificates(AutomationCommand):
    def command_name(self) -> str:
        return "store-broker-certs"

    def get_request(self) -> BrokerCertificates:
        req = _request.get_str_input_mandatory("certificates")
        return BrokerCertificates.model_validate_json(req)

    def execute(self, api_request: BrokerCertificates) -> bool:

        if not api_request:
            raise MKGeneralException(_("Invalid generate-broker-certs: no certificates received."))

        try:
            ca_bytes = api_request.central_ca
            if api_request.customer_ca:
                ca_bytes += api_request.customer_ca
                ca = Certificate.load_pem(CertificatePEM(api_request.customer_ca))
            else:
                ca = Certificate.load_pem(CertificatePEM(api_request.central_ca))
            Certificate.load_pem(CertificatePEM(api_request.cert)).verify_is_signed_by(ca)

            store.save_bytes_to_file(cacert_file(paths.omd_root), ca_bytes)
            store.save_bytes_to_file(cert_file(paths.omd_root), api_request.cert)
            store.save_bytes_to_file(key_file(paths.omd_root), api_request.key)
        except:
            raise MKGeneralException(
                _("Failed to save broker certificates: %s") % traceback.format_exc()
            )

        return True
