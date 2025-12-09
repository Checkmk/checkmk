#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pydantic_core import ErrorDetails

from cmk.gui.dashboard.token_util import (
    DashboardTokenAlreadyExists,
    DashboardTokenExpirationInvalid,
    issue_dashboard_token,
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
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.restful_objects.validators import RequestDataValidator
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import get_token_store

from ._family import DASHBOARD_FAMILY
from ._utils import get_dashboard_for_edit, PERMISSIONS_DASHBOARD_EDIT, save_dashboard_to_file
from .model.token import CreateDashboardToken, DashboardTokenMetadata, DashboardTokenObjectModel


def create_dashboard_token_v1(
    api_context: ApiContext, body: CreateDashboardToken
) -> ApiResponse[DashboardTokenObjectModel]:
    """Creates a new dashboard token and returns its metadata."""
    dashboard = get_dashboard_for_edit(body.dashboard_owner, body.dashboard_id)

    token_store = get_token_store()
    try:
        token = issue_dashboard_token(
            dashboard,
            expiration_time=body.expires_at,
            comment=body.comment,
            token_store=token_store,
        )
    except DashboardTokenAlreadyExists:
        raise ProblemException(
            status=400,
            title="Dashboard token already exists",
            detail="A token for this dashboard already exists, cannot create another one.",
        )
    except DashboardTokenExpirationInvalid as e:
        raise RequestDataValidator.format_error_details(
            [
                ErrorDetails(
                    type="value_error",
                    msg=e.message,
                    loc=("body", "expires_at"),
                    input=body.expires_at,
                )
            ]
        ) from None

    dashboard["public_token_id"] = token.token_id
    try:
        save_dashboard_to_file(api_context.config.sites, dashboard, body.dashboard_owner)
    except:
        # rollback token creation
        token_store.delete(token.token_id)
        raise

    return ApiResponse(
        DashboardTokenObjectModel(
            id=token.token_id,
            domainType="dashboard_token",
            extensions=DashboardTokenMetadata.from_internal(token),
            links=[],
        ),
        status_code=201,
    )


ENDPOINT_CREATE_DASHBOARD_TOKEN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("dashboard_token"),
        link_relation="cmk/create_dashboard_token",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD_EDIT),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=create_dashboard_token_v1)},
)
