#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Certificates

WARNING: Use at your own risk, not supported.

Checkmk uses TLS certificates to secure agent communication.
"""

from collections.abc import Mapping
from typing import Any

from cryptography import x509
from dateutil.relativedelta import relativedelta

from cmk.utils.certs import agent_root_ca_path, cert_dir, CertManagementEvent, RootCA, SiteCA
from cmk.utils.log.security_event import log_security_event
from cmk.utils.paths import omd_root

from cmk.gui import config
from cmk.gui.default_permissions import PERMISSION_SECTION_GENERAL
from cmk.gui.http import Response
from cmk.gui.i18n import _l
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.cert.request_schemas import X509ReqPEMUUID
from cmk.gui.openapi.endpoints.cert.response_schemas import (
    AgentControllerCertificateSettings,
    X509PEM,
)
from cmk.gui.openapi.restful_objects import Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.utils import permission_verification as permissions

from cmk.crypto.certificate import CertificateSigningRequest
from cmk.crypto.x509 import SAN, SubjectAlternativeNames

_403_STATUS_DESCRIPTION = "You do not have the permission for agent pairing."

permission_registry.register(
    Permission(
        section=PERMISSION_SECTION_GENERAL,
        name="agent_pairing",
        title=_l("Agent pairing"),
        description=_l(
            "Only relevant for the agent controller shipped with Checkmk 2.1."
            " Pairing of Checkmk agents with the monitoring site."
            " This step establishes trust between the agent and the monitoring site."
        ),
        defaults=["admin"],
    )
)


def _user_is_authorized() -> bool:
    return user.may("general.agent_pairing")


def _get_agent_ca() -> RootCA:
    return RootCA.load(agent_root_ca_path(omd_root))


def _serialized_root_cert() -> str:
    # loading and dumping the PEM is needed here to ensure that we don't send the private key along
    return SiteCA.load(cert_dir(omd_root)).root_ca.certificate.dump_pem().str


def _serialized_signed_cert(csr: x509.CertificateSigningRequest) -> str:
    csr_ = CertificateSigningRequest(csr)
    if csr_.subject.common_name is None:
        raise ValueError("CSR must provide a common name")
    cert = _get_agent_ca().sign_csr(
        csr_,
        expiry=relativedelta(
            months=config.active_config.agent_controller_certificates["lifetime_in_months"]
        ),
        subject_alternative_names=SubjectAlternativeNames([SAN.dns_name(csr_.subject.common_name)]),
    )
    log_security_event(
        CertManagementEvent(
            event="certificate created",
            component="agent controller",
            actor=user.id,
            cert=cert,
        )
    )

    return cert.dump_pem().str


@Endpoint(
    "/root_cert",
    "cmk/show",
    method="get",
    tag_group="Checkmk Internal",
    additional_status_codes=[403],
    status_descriptions={
        403: _403_STATUS_DESCRIPTION,
    },
    permissions_required=permissions.Perm("general.agent_pairing"),
    response_schema=X509PEM,
)
def root_cert(param: Mapping[str, Any]) -> Response:
    """X.509 PEM-encoded root certificate"""
    if not _user_is_authorized():
        raise ProblemException(
            status=403,
            title="Unauthorized",
            detail=_403_STATUS_DESCRIPTION,
        )
    return serve_json(
        {
            "cert": _serialized_root_cert(),
        }
    )


@Endpoint(
    "/csr",
    "cmk/sign",
    method="post",
    tag_group="Checkmk Internal",
    additional_status_codes=[403],
    status_descriptions={
        403: _403_STATUS_DESCRIPTION,
    },
    request_schema=X509ReqPEMUUID,
    response_schema=X509PEM,
    permissions_required=permissions.Perm("general.agent_pairing"),
)
def make_certificate(param: Mapping[str, Any]) -> Response:
    """X.509 PEM-encoded Certificate Signing Requests (CSRs)"""
    if not _user_is_authorized():
        raise ProblemException(
            status=403,
            title="Unauthorized",
            detail=_403_STATUS_DESCRIPTION,
        )
    return serve_json(
        {
            "cert": _serialized_signed_cert(param["body"]["csr"]),
        }
    )


@Endpoint(
    "/agent_controller_certificates_settings",
    "cmk/global_config",
    method="get",
    tag_group="Checkmk Internal",
    additional_status_codes=[403],
    status_descriptions={
        403: "Unauthorized to read the global settings",
    },
    response_schema=AgentControllerCertificateSettings,
    permissions_required=permissions.AnyPerm(
        [
            permissions.Perm("wato.seeall"),
            permissions.Perm("wato.global"),
        ],
    ),
)
def agent_controller_certificates_settings(param: object) -> Response:
    """Show agent controller certificate settings"""
    if not (user.may("wato.seeall") or user.may("wato.global")):
        raise ProblemException(
            status=403,
            title="Unauthorized",
            detail="Unauthorized to read the global settings",
        )
    return serve_json(config.active_config.agent_controller_certificates)


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(root_cert, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(make_certificate, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(
        agent_controller_certificates_settings, ignore_duplicates=ignore_duplicates
    )
