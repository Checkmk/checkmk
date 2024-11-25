#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
import logging
from collections import defaultdict
from collections.abc import Container, Mapping, Sequence
from dataclasses import dataclass
from typing import IO, Literal

from cryptography.hazmat.primitives.serialization import Encoding

from livestatus import SiteConfiguration, SiteId

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site

from cmk.utils import paths
from cmk.utils.certs import (
    CustomerBrokerCA,
    LocalBrokerCertificate,
    SiteBrokerCA,
    SiteBrokerCertificate,
)

from cmk.gui.http import request as _request
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation

from cmk.crypto.certificate import CertificateSigningRequest, CertificateWithPrivateKey, X509Name
from cmk.crypto.keys import PrivateKey
from cmk.messaging import (
    all_cert_files,
    BrokerCertificates,
    clear_brokers_certs_cache,
    rabbitmq,
)

logger = logging.getLogger("cmk.web.background-job")
_ORG_TEMPLATE = "Checkmk Site {}"
BrokerCertsCSR = Mapping[Literal["csr"], bytes]


class BrokerCertificateSync(abc.ABC):
    def load_central_ca(self) -> SiteBrokerCA:
        return SiteBrokerCA.load(paths.omd_root)

    @abc.abstractmethod
    def broker_certs_created(self, site_id: SiteId, settings: SiteConfiguration) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def get_site_to_sync(
        self, myself: SiteId, dirty_sites: list[tuple[SiteId, SiteConfiguration]]
    ) -> Mapping[str, Sequence[tuple[SiteId, SiteConfiguration]]]:
        raise NotImplementedError

    @abc.abstractmethod
    def load_or_create_customer_ca(self, customer: str) -> CustomerBrokerCA | None:
        raise NotImplementedError

    @abc.abstractmethod
    def create_broker_certificates(
        self,
        site_id: SiteId,
        settings: SiteConfiguration,
        central_ca: SiteBrokerCA,
        customer_ca: CustomerBrokerCA | None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def update_trusted_cas(self) -> None:
        raise NotImplementedError


class DefaultBrokerCertificateSync(BrokerCertificateSync):
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

    def load_or_create_customer_ca(self, customer: str) -> CustomerBrokerCA | None:
        # Only relevant for editions with different customers
        return None

    def create_broker_certificates(
        self,
        site_id: SiteId,
        settings: SiteConfiguration,
        central_ca: SiteBrokerCA,
        customer_ca: CustomerBrokerCA | None,
    ) -> None:
        logger.debug("Start creating broker certificates for site %s", site_id)
        remote_broker_certs = create_remote_broker_certs(central_ca, site_id, settings)

        logger.debug("Start syncing broker certificates for site %s", site_id)
        sync_remote_broker_certs(settings, remote_broker_certs)
        logger.debug("Certificates synced")

        # the presence of the following cert is used to determine if the broker certificates need
        # to be created/synced, so only save it if the sync was successful
        LocalBrokerCertificate.write(site_id, paths.omd_root, remote_broker_certs.cert)

    def update_trusted_cas(self) -> None:
        # Only relevant for editions with different customers
        pass


def broker_certs_created(site_id: SiteId) -> bool:
    return LocalBrokerCertificate.exists(site_id, paths.omd_root)


def create_remote_broker_certs(
    signing_ca: SiteBrokerCA, site_id: SiteId, site: SiteConfiguration
) -> BrokerCertificates:
    """
    Create a new certificate with private key for the broker of a remote site.
    """

    site_cert = SiteBrokerCertificate.create(site_id, paths.omd_root, signing_ca.cert_bundle)

    return BrokerCertificates(
        key=site_cert.cert_bundle.private_key.dump_pem(None).bytes,
        cert=site_cert.cert_bundle.certificate.dump_pem().bytes,
        signing_ca=signing_ca.cert_bundle.certificate.dump_pem().bytes,
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
        [("certificates", broker_certificates.model_dump_json()), ("site_id", omd_site())],
        timeout=60,
    )


def clean_dead_sites_certs(alive_sites: Container[SiteId]) -> None:
    """
    Remove broker certificates for sites that no longer exist.
    """

    for cert in all_cert_files(omd_root=paths.omd_root):
        if SiteId(cert.name.removesuffix("_cert.pem")) not in alive_sites:
            cert.unlink(missing_ok=True)


def _create_message_broker_certs() -> CertificateWithPrivateKey:
    """Initialize the CA and create the certificate for use with the message broker.
    These might be replaced by the "store-broker-certs" automation.
    """

    ca = SiteBrokerCA.create_and_persist(omd_site(), paths.omd_root)
    ca.write_trusted_cas_file(paths.omd_root)

    site_cert = SiteBrokerCertificate.create(omd_site(), paths.omd_root, issuer=ca.cert_bundle)
    site_cert.persist(paths.omd_root)

    return site_cert.cert_bundle


def _create_csr(private_key: PrivateKey) -> CertificateSigningRequest:
    site_name = omd_site()
    return CertificateSigningRequest.create(
        subject_name=X509Name.create(
            common_name=site_name,
            organization_name=_ORG_TEMPLATE.format(site_name),
        ),
        subject_private_key=private_key,
    )


@dataclass(frozen=True)
class StoreBrokerCertificatesData:
    certificates: BrokerCertificates
    central_site: SiteId


class AutomationStoreBrokerCertificates(AutomationCommand[StoreBrokerCertificatesData]):
    def _add_central_site_user(self, central_site: SiteId) -> None:
        def _handle_errors(command: tuple[str, ...]) -> IO[str] | None:
            popen = rabbitmq.rabbitmqctl_process(command)
            if popen.stderr and (lines := popen.stderr.readlines()):
                logger.error(
                    "Failed to execute command: %s, with error: %s",
                    command,
                    "".join(lines),
                )
                raise MKGeneralException(f"Failed to execute command: {command}")
            return popen.stdout

        rabbitmq.rabbitmqctl_process(("add_user", central_site, "password"))
        # the password here is used to avoid the process waiting for input
        # it is removed in the next command
        _handle_errors(("clear_password", central_site))
        user_permissions = rabbitmq.make_default_remote_user_permission(central_site)
        _handle_errors(
            (
                "set_permissions",
                "-p",
                user_permissions.vhost,
                user_permissions.user,
                user_permissions.configure,
                user_permissions.write,
                user_permissions.read,
            )
        )

    def command_name(self) -> str:
        return "store-broker-certs"

    def get_request(self) -> StoreBrokerCertificatesData:
        request_certificates = _request.get_str_input_mandatory("certificates")
        request_site = _request.get_str_input_mandatory("site_id")
        return StoreBrokerCertificatesData(
            certificates=BrokerCertificates.model_validate_json(request_certificates),
            central_site=SiteId(request_site),
        )

    def execute(self, api_request: StoreBrokerCertificatesData) -> bool:
        SiteBrokerCertificate.persist_broker_certificates(paths.omd_root, api_request.certificates)

        # Remove local CA files to avoid confusion. They have no use anymore.
        SiteBrokerCA.delete(paths.omd_root)

        self._add_central_site_user(api_request.central_site)
        clear_brokers_certs_cache()

        return True


class AutomationCreateBrokerCertificates(AutomationCommand[None]):
    def command_name(self) -> str:
        return "create-broker-certs"

    def get_request(self) -> None:
        pass

    def execute(self, api_request: None) -> BrokerCertsCSR:
        private_key = _create_message_broker_certs().private_key
        return {"csr": _create_csr(private_key).csr.public_bytes(Encoding.PEM)}
