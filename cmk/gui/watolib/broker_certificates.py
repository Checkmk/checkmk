#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path

from dateutil.relativedelta import relativedelta

from livestatus import SiteConfiguration, SiteId

from cmk.ccc import store
from cmk.ccc.site import omd_site

from cmk.utils import paths
from cmk.utils.certs import save_single_cert

from cmk.gui.http import request as _request
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
    multisite_cert_file,
    site_cert_file,
    site_key_file,
    trusted_cas_file,
)


class BrokerCertificateSync(abc.ABC):
    def load_central_ca(self) -> PersistedCertificateWithPrivateKey:
        return load_broker_ca(paths.omd_root)

    @abc.abstractmethod
    def broker_certs_created(self, site_id: SiteId, settings: SiteConfiguration) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def get_site_to_sync(
        self, myself: SiteId, dirty_sites: list[tuple[SiteId, SiteConfiguration]]
    ) -> Mapping[str, Sequence[tuple[SiteId, SiteConfiguration]]]:
        raise NotImplementedError

    @abc.abstractmethod
    def load_or_create_customer_ca(
        self, customer: str
    ) -> PersistedCertificateWithPrivateKey | None:
        raise NotImplementedError

    @abc.abstractmethod
    def create_broker_certificates(
        self,
        site_id: SiteId,
        settings: SiteConfiguration,
        central_ca: CertificateWithPrivateKey,
        customer_ca: CertificateWithPrivateKey | None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def update_trusted_cas(self) -> None:
        raise NotImplementedError


class CREBrokerCertificateSync(BrokerCertificateSync):
    def broker_certs_created(self, site_id: SiteId, settings: SiteConfiguration) -> bool:
        return broker_certs_created(site_id)

    def get_site_to_sync(
        self, myself: SiteId, dirty_sites: list[tuple[SiteId, SiteConfiguration]]
    ) -> Mapping[str, Sequence[tuple[SiteId, SiteConfiguration]]]:
        required_certificates: dict[str, list[tuple[SiteId, SiteConfiguration]]] = defaultdict(list)
        for site_id, settings in dirty_sites:
            if site_id != myself and not self.broker_certs_created(site_id, settings):
                required_certificates["provider"].append((site_id, settings))
        return required_certificates

    def load_or_create_customer_ca(
        self, customer: str
    ) -> PersistedCertificateWithPrivateKey | None:
        # Only relevant for editions with different customers
        return None

    def create_broker_certificates(
        self,
        site_id: SiteId,
        settings: SiteConfiguration,
        central_ca: CertificateWithPrivateKey,
        customer_ca: CertificateWithPrivateKey | None,
    ) -> None:
        sync_remote_broker_certs(
            settings, create_remote_broker_certs(central_ca, site_id, settings)
        )

    def update_trusted_cas(self) -> None:
        # Only relevant for editions with different customers
        pass


def create_broker_certs(
    cert_path: Path, site_id: SiteId, ca: CertificateWithPrivateKey
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


def load_broker_ca(omd_root: Path) -> PersistedCertificateWithPrivateKey:
    return PersistedCertificateWithPrivateKey.read_files(
        cacert_file(omd_root), ca_key_file(omd_root)
    )


def broker_certs_created(site_id: SiteId) -> bool:
    return multisite_cert_file(paths.omd_root, site_id).exists()


def create_remote_broker_certs(
    signing_ca: CertificateWithPrivateKey, site_id: SiteId, site: SiteConfiguration
) -> BrokerCertificates:
    """
    Create a new certificate with private key for the broker of a remote site.
    """

    cert_key = create_broker_certs(
        multisite_cert_file(paths.omd_root, site_id),
        site_id,
        signing_ca,
    )
    return BrokerCertificates(
        key=cert_key.private_key.dump_pem(None).bytes,
        cert=cert_key.certificate.dump_pem().bytes,
        signing_ca=signing_ca.certificate.dump_pem().bytes,
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
        ca = Certificate.load_pem(CertificatePEM(api_request.signing_ca))
        Certificate.load_pem(CertificatePEM(api_request.cert)).verify_is_signed_by(ca)

        store.save_bytes_to_file(
            trusted_cas_file(paths.omd_root),
            api_request.signing_ca + api_request.additionally_trusted_ca,
        )
        store.save_bytes_to_file(site_cert_file(paths.omd_root), api_request.cert)
        store.save_bytes_to_file(site_key_file(paths.omd_root), api_request.key)
        cacert_file(paths.omd_root).unlink(missing_ok=True)
        ca_key_file(paths.omd_root).unlink(missing_ok=True)

        return True
