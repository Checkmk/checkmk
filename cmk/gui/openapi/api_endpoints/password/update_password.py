#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from pydantic import AfterValidator

from cmk.ccc.site import omd_site
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import PasswordConverter
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.user_sites import activation_sites
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.passwords import load_password, load_password_to_modify, save_password
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.sidebar_reload import sidebar_reload_change_hook

from .endpoint_family import PASSWORD_FAMILY
from .models.request_models import UpdatePassword
from .models.response_models import PasswordObject
from .utils import password_etag, RW_PERMISSIONS, serialize_password


def update_password_v1(
    api_context: ApiContext,
    name: Annotated[
        str,
        AfterValidator(PasswordConverter.exists),
        PathParam(
            description="A name used as an identifier. Can be of arbitrary (sensible) length.",
            example="pathname",
        ),
    ],
    body: UpdatePassword,
) -> ApiResponse[PasswordObject]:
    """Update a password"""
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")
    original_config = load_password_to_modify(name)
    if api_context.etag.enabled:
        api_context.etag.verify(password_etag(name, original_config))

    password_details = body.update(original_config)
    save_password(
        name,
        password_details,
        new_password=False,
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
    password = load_password(name)
    return ApiResponse(
        status_code=200,
        body=serialize_password(name, password),
        etag=password_etag(name, password),
    )


ENDPOINT_UPDATE_PASSWORD = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("password", "{name}"),
        link_relation=".../update",
        method="put",
    ),
    behavior=EndpointBehavior(etag="both"),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=PASSWORD_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=update_password_v1)},
)
