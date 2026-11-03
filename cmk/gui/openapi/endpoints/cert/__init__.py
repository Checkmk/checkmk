#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Certificates

WARNING: Use at your own risk, not supported.

Checkmk uses TLS certificates to secure agent communication.
"""

from http import HTTPStatus

from cmk.gui import config
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.cert.response_schemas import AgentControllerCertificateSettings
from cmk.gui.openapi.restful_objects import Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.web.utils import permission_verification as permissions


@Endpoint(
    "/agent_controller_certificates_settings",
    "cmk/global_config",
    method="get",
    tag_group="Checkmk Internal",
    additional_status_codes=[HTTPStatus.FORBIDDEN],
    status_descriptions={
        HTTPStatus.FORBIDDEN: "Unauthorized to read the global settings",
    },
    response_schema=AgentControllerCertificateSettings,
    permissions_required=permissions.AnyPerm(
        [
            permissions.Perm("wato.seeall"),
            permissions.Perm("wato.global"),
        ],
    ),
)
def agent_controller_certificates_settings(param: object) -> Response:  # noqa: ARG001
    """Show agent controller certificate settings"""
    if not (user.may("wato.seeall") or user.may("wato.global")):
        raise ProblemException(
            status=HTTPStatus.FORBIDDEN,
            title="Unauthorized",
            detail="Unauthorized to read the global settings",
        )
    return serve_json(config.active_config.agent_controller_certificates)


def register(endpoint_registry: EndpointRegistry) -> None:
    endpoint_registry.register(agent_controller_certificates_settings)
