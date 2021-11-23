#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Certificates

WARNING: Use at your own risk, not supported.

Checkmk uses SSL certificates to verify push hosts.
"""


from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509 import CertificateSigningRequest

from cmk.utils.certs import sign_csr_with_local_ca

from cmk.gui.default_permissions import PermissionSectionGeneral
from cmk.gui.globals import user
from cmk.gui.http import Response
from cmk.gui.i18n import _l
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.utils import ProblemException

_403_STATUS_DESCRIPTION = "You do not have the permission to post CSRs."

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="post_csr_rest_api",
        title=_l("Post Certificate Signing Requests (CSRs) via REST API"),
        description=_l(
            "Post CSRs via the REST API. They will be signed by the local site CA. This used by "
            "the Checkmk agent controller during the registration of new hosts."
        ),
        defaults=["admin"],
    )
)


def _user_is_authorized() -> bool:
    return user.may("general.post_csr_rest_api")


def _serialized_signed_cert(csr: CertificateSigningRequest) -> str:
    return (
        sign_csr_with_local_ca(
            csr,
            365 * 999,
        )
        .public_bytes(Encoding.PEM)
        .decode()
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
)
def make_certificate(param) -> Response:
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
