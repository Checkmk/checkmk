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
from cryptography.x509 import CertificateSigningRequest as x509CertificateSigningRequest
from cryptography.x509 import load_pem_x509_csr
from dateutil.relativedelta import relativedelta

from livestatus import SiteConfiguration

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import omd_site, SiteId

from cmk.utils import paths
from cmk.utils.certs import (
    LocalBrokerCertificate,
    MessagingTrustedCAs,
    SiteBrokerCA,
    SiteBrokerCertificate,
)

from cmk.gui.http import request as _request
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation, RemoteAutomationConfig

from cmk import messaging
from cmk.crypto.certificate import (
    CertificateSigningRequest,
    CertificateWithPrivateKey,
    PersistedCertificateWithPrivateKey,
)
from cmk.crypto.keys import PrivateKey
from cmk.crypto.x509 import (
    SAN,
    SubjectAlternativeNames,
    X509Name,
)

logger = logging.getLogger("cmk.web.background-job")
_ORG_TEMPLATE = "Checkmk Site {}"
BrokerCertsCSR = Mapping[Literal["csr"], bytes]


class BrokerCertificateSync(abc.ABC):
    def load_central_ca(self) -> PersistedCertificateWithPrivateKey:
        return SiteBrokerCA(
            messaging.cacert_file(paths.omd_root), messaging.ca_key_file(paths.omd_root)
        ).load()

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
        automation_config: RemoteAutomationConfig,
        central_ca_bundle: PersistedCertificateWithPrivateKey,
        customer_ca_bundle: PersistedCertificateWithPrivateKey | None,
        *,
        debug: bool,
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

    def load_or_create_customer_ca(
        self, customer: str
    ) -> PersistedCertificateWithPrivateKey | None:
        # Only relevant for editions with different customers
        return None

    def create_broker_certificates(
        self,
        automation_config: RemoteAutomationConfig,
        central_ca_bundle: PersistedCertificateWithPrivateKey,
        customer_ca_bundle: PersistedCertificateWithPrivateKey | None,
        *,
        debug: bool,
    ) -> None:
        logger.info("Remote broker certificates creation for site %s", automation_config.site_id)
        csr = CertificateSigningRequest(ask_remote_csr(automation_config, debug=debug))
        if csr.subject.common_name is None:
            raise ValueError("CSR must provide a common name")

        signed = central_ca_bundle.sign_csr(
            csr,
            relativedelta(years=2),
            SubjectAlternativeNames([SAN.dns_name(csr.subject.common_name)]),
        )

        remote_broker_certs = messaging.BrokerCertificates(
            cert=signed.dump_pem().bytes,
            signing_ca=central_ca_bundle.certificate.dump_pem().bytes,
        )

        logger.info("Sending signed broker certificates for site %s", automation_config.site_id)
        _sync_broker_certs(automation_config, remote_broker_certs, debug=debug)

        # the presence of the following cert is used to determine if the broker certificates need
        # to be created/synced, so only save it if the sync was successful
        LocalBrokerCertificate(
            messaging.multisite_cert_file(paths.omd_root, automation_config.site_id)
        ).write(remote_broker_certs.cert)

    def update_trusted_cas(self) -> None:
        # Only relevant for editions with different customers
        pass


def _sync_broker_certs(
    automation_config: RemoteAutomationConfig,
    remote_broker_certs: messaging.BrokerCertificates,
    *,
    debug: bool,
) -> None:
    do_remote_automation(
        automation_config,
        "store-broker-certs",
        [("certificates", remote_broker_certs.model_dump_json()), ("site_id", omd_site())],
        timeout=120,
        debug=debug,
    )


def ask_remote_csr(
    automation_config: RemoteAutomationConfig, *, debug: bool
) -> x509CertificateSigningRequest:
    raw_response = do_remote_automation(
        automation_config,
        "create-broker-certs",
        [],
        timeout=60,
        debug=debug,
    )

    match raw_response:
        case {"csr": bytes(raw_csr)}:
            return load_pem_x509_csr(raw_csr)

    raise ValueError(raw_response)


def broker_certs_created(site_id: SiteId) -> bool:
    return LocalBrokerCertificate(messaging.multisite_cert_file(paths.omd_root, site_id)).exists()


def create_remote_broker_certs(
    signing_ca_bundle: PersistedCertificateWithPrivateKey, site_id: SiteId, site: SiteConfiguration
) -> messaging.BrokerCertificates:
    """
    Create a new certificate with private key for the broker of a remote site.
    """

    site_broker_ca = SiteBrokerCertificate(
        messaging.site_cert_file(paths.omd_root), messaging.site_key_file(paths.omd_root)
    )
    site_ca_bundle = site_broker_ca.create_bundle(site_id, signing_ca_bundle)

    return messaging.BrokerCertificates(
        cert=site_ca_bundle.certificate.dump_pem().bytes,
        signing_ca=signing_ca_bundle.certificate.dump_pem().bytes,
    )


def sync_remote_broker_certs(
    automation_config: RemoteAutomationConfig,
    broker_certificates: messaging.BrokerCertificates,
    *,
    debug: bool,
) -> None:
    """
    Send the broker certificates to the remote site for storage.
    """

    do_remote_automation(
        automation_config,
        "store-broker-certs",
        [("certificates", broker_certificates.model_dump_json()), ("site_id", omd_site())],
        timeout=120,
        debug=debug,
    )


def clean_remote_sites_certs(*, kept_sites: Container[SiteId]) -> None:
    """
    Remove broker certificates of remote sites.
    """

    for cert in messaging.all_cert_files(omd_root=paths.omd_root):
        if SiteId(cert.name.removesuffix("_cert.pem")) in kept_sites:
            continue
        cert.unlink(missing_ok=True)


def trigger_remote_certs_creation(
    site_id: SiteId, settings: SiteConfiguration, *, force: bool, debug: bool
) -> None:
    broker_sync = broker_certificate_sync_registry["broker_certificate_sync"]
    if not force and broker_sync.broker_certs_created(site_id, settings):
        return

    central_ca = broker_sync.load_central_ca()
    customer_ca = broker_sync.load_or_create_customer_ca(settings.get("customer", "provider"))
    broker_sync.create_broker_certificates(
        RemoteAutomationConfig.from_site_config(settings), central_ca, customer_ca, debug=debug
    )
    broker_sync.update_trusted_cas()


class BrokerCertificateSyncRegistry(Registry[BrokerCertificateSync]):
    def plugin_name(self, instance: BrokerCertificateSync) -> str:
        return "broker_certificate_sync"


broker_certificate_sync_registry = BrokerCertificateSyncRegistry()


def _create_message_broker_certs() -> CertificateWithPrivateKey:
    """Initialize the CA and create the certificate for use with the message broker.
    These might be replaced by the "store-broker-certs" automation.
    """

    ca = SiteBrokerCA(messaging.cacert_file(paths.omd_root), messaging.ca_key_file(paths.omd_root))
    ca_bundle = ca.create_and_persist(omd_site())
    MessagingTrustedCAs(messaging.trusted_cas_file(paths.omd_root)).write(
        ca_bundle.certificate_path.read_bytes()
    )

    site_broker_ca = SiteBrokerCertificate(
        messaging.site_cert_file(paths.omd_root), messaging.site_key_file(paths.omd_root)
    )
    site_broker_ca.persist(bundle := site_broker_ca.create_bundle(omd_site(), issuer=ca_bundle))

    return bundle


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
    certificates: messaging.BrokerCertificates
    central_site: SiteId


class AutomationStoreBrokerCertificates(AutomationCommand[StoreBrokerCertificatesData]):
    def _add_central_site_user(self, central_site: SiteId) -> None:
        def _handle_errors(command: tuple[str, ...]) -> IO[str] | None:
            popen = messaging.rabbitmq.rabbitmqctl_process(command, wait=True)
            if popen.stderr and (lines := popen.stderr.readlines()):
                logger.error(
                    "Failed to execute command: %s, with error: %s",
                    command,
                    "".join(lines),
                )
                raise MKGeneralException(f"Failed to execute command: {command}")
            return popen.stdout

        messaging.rabbitmq.rabbitmqctl_process(("add_user", central_site, "password"), wait=True)
        # the password here is used to avoid the process waiting for input
        # it is removed in the next command
        _handle_errors(("clear_password", central_site))
        user_permissions = messaging.rabbitmq.make_default_remote_user_permission(central_site)
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
            certificates=messaging.BrokerCertificates.model_validate_json(request_certificates),
            central_site=SiteId(request_site),
        )

    def execute(self, api_request: StoreBrokerCertificatesData) -> bool:
        trusted_cas_store = MessagingTrustedCAs(messaging.trusted_cas_file(paths.omd_root))
        SiteBrokerCertificate(
            messaging.site_cert_file(paths.omd_root), messaging.site_key_file(paths.omd_root)
        ).persist_broker_certificates(
            signing_ca=api_request.certificates.signing_ca,
            cert=api_request.certificates.cert,
            additionally_trusted_ca=api_request.certificates.additionally_trusted_ca,
            trusted_cas_store=trusted_cas_store,
        )

        # Remove local CA files to avoid confusion. They have no use anymore.
        SiteBrokerCA(
            messaging.cacert_file(paths.omd_root), messaging.ca_key_file(paths.omd_root)
        ).delete()

        # In case we're logging in, and the node is running, immediately create the user.
        # If for some reason the node is not running, the user will be created when the
        # node starts and imports the definitions.
        if messaging.rabbitmq.rabbitmqctl_process(("status",), wait=True).returncode == 0:
            messaging.clear_brokers_certs_cache()
            self._add_central_site_user(api_request.central_site)

        return True


class AutomationCreateBrokerCertificates(AutomationCommand[None]):
    def command_name(self) -> str:
        return "create-broker-certs"

    def get_request(self) -> None:
        pass

    def execute(self, api_request: None) -> BrokerCertsCSR:
        private_key = _create_message_broker_certs().private_key
        return {"csr": _create_csr(private_key).csr.public_bytes(Encoding.PEM)}
