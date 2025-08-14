#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import ApiContext, PathParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.converter import (
    SiteIdConverter,
    TypedPlainValidator,
    UserConverter,
)
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException
from cmk.gui.watolib.site_management import (
    LoginException,
    SitesApiMgr,
)

from .endpoint_family import SITE_MANAGEMENT_FAMILY
from .utils import LOGIN_PERMISSIONS


@api_model
class SiteLoginCredentials:
    username: Annotated[
        UserId,
        TypedPlainValidator(str, UserConverter.valid_user_id),
    ] = api_field(
        description="An administrative user's username.",
        example="cmkadmin",
    )
    password: str = api_field(
        description="The password for the username given",
        example="password",
    )


def site_connection_login_v1(
    api_context: ApiContext,
    site_id: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_exist),
        PathParam(description="An existing site ID.", example="prod"),
    ],
    body: SiteLoginCredentials,
) -> None:
    """Login to a remote site"""
    user.need_permission("wato.sites")
    # TODO: Cleanup - remove this permission
    # We only check that the username complies to a restricted set of allowed characters.
    # "wato.users" is not a required permission, but it was before the migration.
    user.need_permission("wato.users")
    try:
        SitesApiMgr().login_to_site(
            site_id=site_id,
            username=body.username,
            password=body.password,
            pprint_value=api_context.config.wato_pprint_config,
            debug=api_context.config.debug,
        )
    except LoginException as exc:
        raise RestAPIRequestGeneralException(
            status=400,
            title="Login problem",
            detail=str(exc),
        )


ENDPOINT_SITE_CONNECTION_LOGIN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("site_connection", "{site_id}", "login"),
        link_relation="cmk/site_login",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=LOGIN_PERMISSIONS),
    doc=EndpointDoc(family=SITE_MANAGEMENT_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=site_connection_login_v1)},
)
