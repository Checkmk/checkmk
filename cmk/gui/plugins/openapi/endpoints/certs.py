#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Certificates

WARNING: Use at your own risk, not supported.

Checkmk uses SSL certificates to verify push hosts.
"""
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509 import CertificateSigningRequest

from cmk.utils.certs import cert_dir, root_cert_path, RootCA
from cmk.utils.paths import omd_root

from cmk.gui.default_permissions import PermissionSectionGeneral
from cmk.gui.globals import user
from cmk.gui.http import Response
from cmk.gui.i18n import _l
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    permissions,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.utils import ProblemException

_403_STATUS_DESCRIPTION = "You do not have the permission for agent pairing."

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="agent_pairing",
        title=_l("Agent pairing"),
        description=_l(
            "Pairing of Checkmk agents with the monitoring site. This step establishes trust "
            "between the agent and the monitoring site."
        ),
        defaults=["admin"],
    )
)


def _user_is_authorized() -> bool:
    return user.may("general.agent_pairing")


def _get_root_ca() -> RootCA:
    return RootCA.load(root_cert_path(cert_dir(Path(omd_root))))


def _serialized_root_cert() -> str:
    return _get_root_ca().cert.public_bytes(Encoding.PEM).decode()


def _serialized_signed_cert(csr: CertificateSigningRequest) -> str:
    return _get_root_ca().sign_csr(csr).public_bytes(Encoding.PEM).decode()


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
    response_schema=response_schemas.X509PEM,
)
def root_cert(param: Mapping[str, Any]) -> Response:
    """X.509 PEM-encoded root certificate"""
    if not _user_is_authorized():
        raise ProblemException(
            status=403,
            title=_403_STATUS_DESCRIPTION,
        )
    return constructors.serve_json(
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
    request_schema=request_schemas.X509ReqPEM,
    response_schema=response_schemas.X509PEM,
    permissions_required=permissions.Perm("general.agent_pairing"),
)
def make_certificate(param: Mapping[str, Any]) -> Response:
    """X.509 PEM-encoded Certificate Signing Requests (CSRs)"""
    if not _user_is_authorized():
        raise ProblemException(
            status=403,
            title=_403_STATUS_DESCRIPTION,
        )
    return constructors.serve_json(
        {
            "cert": _serialized_signed_cert(param["body"]["csr"]),
        }
    )
