#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from contextlib import suppress

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import get_token_store, TokenId

from ._family import DASHBOARD_FAMILY
from ._utils import get_dashboard_for_edit, PERMISSIONS_DASHBOARD_EDIT, save_dashboard_to_file
from .model.token import DeleteDashboardToken


def delete_dashboard_token_v1(api_context: ApiContext, body: DeleteDashboardToken) -> None:
    """Deletes an existing dashboard token."""
    dashboard = get_dashboard_for_edit(body.dashboard_owner, body.dashboard_id)

    if not (token_id := dashboard.get("public_token_id")):
        raise ProblemException(
            status=404,
            title="Dashboard token not found",
            detail="No token for this dashboard exists.",
        )

    token_store = get_token_store()
    with suppress(KeyError):
        token_store.delete(TokenId(token_id))

    del dashboard["public_token_id"]
    save_dashboard_to_file(api_context.config.sites, dashboard, body.dashboard_owner)


ENDPOINT_DELETE_DASHBOARD_TOKEN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("dashboard_token", "delete"),
        link_relation="cmk/delete_dashboard_token",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD_EDIT),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=delete_dashboard_token_v1)},
)
