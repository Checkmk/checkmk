#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.password.endpoint_family import PASSWORD_FAMILY
from cmk.gui.openapi.api_endpoints.password.models.request_models import CreatePassword
from cmk.gui.openapi.api_endpoints.password.models.response_models import PasswordObject
from cmk.gui.openapi.api_endpoints.password.utils import RW_PERMISSIONS, serialize_password
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.watolib.passwords import load_password, save_password


def create_password_v1(body: CreatePassword) -> PasswordObject:
    """Create a password"""
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")
    ident = body.ident
    save_password(
        ident,
        body.to_internal(),
        new_password=True,
        user_id=user.id,
        pprint_value=active_config.wato_pprint_config,
        use_git=active_config.wato_use_git,
    )
    return serialize_password(ident, load_password(ident))


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
