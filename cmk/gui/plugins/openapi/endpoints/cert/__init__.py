#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Certificates

WARNING: Use at your own risk, not supported.

Checkmk uses TLS certificates to secure agent communication.
"""
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509 import CertificateSigningRequest
from dateutil.relativedelta import relativedelta

from cmk.utils.certs import cert_dir, root_cert_path, RootCA
from cmk.utils.paths import omd_root

import cmk.gui.config as config
from cmk.gui.default_permissions import PermissionSectionGeneral
from cmk.gui.http import Response
from cmk.gui.i18n import _l
from cmk.gui.logged_in import user
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.plugins.openapi.endpoints.cert.request_schemas import X509ReqPEMUUID
from cmk.gui.plugins.openapi.endpoints.cert.response_schemas import (
    AgentControllerCertificateSettings,
    X509PEM,
)
from cmk.gui.plugins.openapi.restful_objects import Endpoint, permissions
from cmk.gui.plugins.openapi.utils import ProblemException, serve_json

_403_STATUS_DESCRIPTION = "You do not have the permission for agent pairing."

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
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


def _get_root_ca() -> RootCA:
    return RootCA.load(root_cert_path(cert_dir(Path(omd_root))))


def _get_agent_ca() -> RootCA:
    return RootCA.load(root_cert_path(cert_dir(Path(omd_root)) / "agents"))


def _serialized_root_cert() -> str:
    return _get_root_ca().cert.public_bytes(Encoding.PEM).decode()


def _serialized_signed_cert(csr: CertificateSigningRequest) -> str:
    return (
        _get_agent_ca()
        .sign_csr(
            csr,
            validity=relativedelta(
                months=config.active_config.agent_controller_certificates["lifetime_in_months"]
            ),
        )
        .public_bytes(Encoding.PEM)
        .decode()
    )


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
            title=_403_STATUS_DESCRIPTION,
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
            title=_403_STATUS_DESCRIPTION,
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
