#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from pathlib import Path

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
from cmk.crypto.certificate import Certificate
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
) -> tuple[Certificate, PrivateKey] | None:
    # if public key is already present,
    # I assume I already created everything for this site in the past
    if not cert_path.exists():
        cert, key = ca.issue_new_certificate(
            common_name=site_id,
        )

        save_single_cert(cert_path, cert)
        if omd_site() == site_id:
            save_single_key(key_path, key)
        return cert, key

    return None


def _load_create_site_cert(site_id: SiteId, ca: RootCA) -> tuple[Certificate, PrivateKey] | None:
    cert_path = multisite_cert_file(paths.omd_root, site_id)
    key_path = multisite_key_file(paths.omd_root, site_id)
    return site_cert(cert_path, key_path, site_id, ca)


def generate_local_broker_ca() -> RootCA:
    return RootCA.load_or_create(
        multisite_cacert_file(paths.omd_root),
        "Central site CA",
    )


def remote_broker_certificates(
    central_site_ca: RootCA, site_id: SiteId, site: SiteConfiguration
) -> BrokerCertificates | None:

    sync_cas = [central_site_ca.certificate.dump_pem().bytes]

    if (cert_key := _load_create_site_cert(site_id, central_site_ca)) is None:
        return None

    return BrokerCertificates(
        key=cert_key[1].dump_pem(None).bytes,
        cert=cert_key[0].dump_pem().bytes,
        cas=sync_cas,
    )


def generate_remote_broker_certificate(
    central_site_ca: RootCA, site_id: SiteId, site: SiteConfiguration
) -> bool:

    if (broker_certificates := remote_broker_certificates(central_site_ca, site_id, site)) is None:
        return False

    do_remote_automation(
        site,
        "store-broker-certs",
        [("certificates", broker_certificates.model_dump_json())],
        timeout=60,
    )

    return True


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
    def command_name(self):
        return "store-broker-certs"

    def get_request(self):
        req = _request.get_str_input_mandatory("certificates")
        return BrokerCertificates.model_validate_json(req)

    def execute(self, api_request):

        if not api_request:
            raise MKGeneralException(_("Invalid generate-broker-certs: no certificates received."))

        try:
            store.save_bytes_to_file(key_file(paths.omd_root), api_request.key)
            store.save_bytes_to_file(cert_file(paths.omd_root), api_request.cert)
            store.save_bytes_to_file(cacert_file(paths.omd_root), b"".join(api_request.cas))
        except:
            raise MKGeneralException(
                _("Failed to save broker certificates: %s") % traceback.format_exc()
            )

        return True
