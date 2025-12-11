#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pydantic_core import ErrorDetails

from cmk.gui.dashboard.token_util import (
    DashboardTokenExpirationInvalid,
    DashboardTokenNotFound,
    InvalidDashboardTokenReference,
    update_dashboard_token,
)
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
from cmk.gui.openapi.restful_objects.validators import RequestDataValidator
from cmk.gui.openapi.utils import ProblemException

from ._family import DASHBOARD_FAMILY
from ._utils import get_dashboard_for_edit, PERMISSIONS_DASHBOARD_EDIT, save_dashboard_to_file
from .model.token import DashboardTokenMetadata, DashboardTokenObjectModel, EditDashboardToken


def edit_dashboard_token_v1(
    api_context: ApiContext, body: EditDashboardToken
) -> DashboardTokenObjectModel:
    """Edit a dashboard token and returns its metadata."""
    dashboard = get_dashboard_for_edit(body.dashboard_owner, body.dashboard_id)

    try:
        token = update_dashboard_token(dashboard, body.is_disabled, body.expires_at, body.comment)
    except (InvalidDashboardTokenReference, DashboardTokenNotFound) as e:
        if isinstance(e, InvalidDashboardTokenReference):
            # remove invalid token reference
            dashboard["public_token_id"] = None
            save_dashboard_to_file(api_context.config.sites, dashboard, body.dashboard_owner)
        raise ProblemException(
            status=404,
            title="Dashboard token not found",
            detail="No token for this dashboard exists.",
        ) from None
    except DashboardTokenExpirationInvalid as e:
        raise RequestDataValidator.format_error_details(
            [
                ErrorDetails(
                    type="value_error",
                    msg=e.message,
                    loc=("body", "expires_at"),
                    input=body.expires_at.isoformat() if body.expires_at else None,
                )
            ]
        ) from None

    return DashboardTokenObjectModel(
        id=token.token_id,
        domainType="dashboard_token",
        extensions=DashboardTokenMetadata.from_internal(token),
        links=[],
    )


ENDPOINT_EDIT_DASHBOARD_TOKEN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("dashboard_token", "edit"),
        link_relation="cmk/edit_dashboard_token",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD_EDIT),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=edit_dashboard_token_v1)},
)
