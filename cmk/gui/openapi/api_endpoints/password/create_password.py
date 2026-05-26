#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.site import omd_site
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.password.endpoint_family import PASSWORD_FAMILY
from cmk.gui.openapi.api_endpoints.password.models.request_models import CreatePassword
from cmk.gui.openapi.api_endpoints.password.models.response_models import PasswordObject
from cmk.gui.openapi.api_endpoints.password.utils import (
    password_etag,
    RW_PERMISSIONS,
    serialize_password,
)
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.user_sites import activation_sites
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.passwords import load_password, save_password
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.sidebar_reload import sidebar_reload_change_hook


def create_password_v1(
    api_context: ApiContext, body: CreatePassword
) -> ApiResponse[PasswordObject]:
    """Create a password"""
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")
    ident = body.ident
    save_password(
        ident,
        body.to_internal(),
        new_password=True,
        pprint_value=api_context.config.wato_pprint_config,
        pending_changes=PendingChanges(
            activation_sites=activation_sites(api_context.config.sites),
            local_site=omd_site(),
            acting_user=user.id,
            store=PendingChangesStore(),
            hooks=(
                make_audit_log_change_hook(use_git=api_context.config.wato_use_git),
                sidebar_reload_change_hook,
                index_update_change_hook,
            ),
        ),
    )
    password = load_password(ident)
    return ApiResponse(
        status_code=200,
        body=serialize_password(ident, password),
        etag=password_etag(ident, password),
    )


ENDPOINT_CREATE_PASSWORD = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("password"),
        link_relation="cmk/create",
        method="post",
    ),
    behavior=EndpointBehavior(etag="output"),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=PASSWORD_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=create_password_v1)},
)
