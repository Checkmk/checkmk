#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from pydantic import AfterValidator

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
from cmk.gui.watolib.passwords import load_password, load_password_to_modify, save_password

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
    original_password = load_password_to_modify(name)
    if api_context.etag.enabled:
        api_context.etag.verify(password_etag(name, original_password))

    password_details = body.update(original_password)
    save_password(
        name,
        password_details,
        new_password=False,
        user_id=user.id,
        pprint_value=api_context.config.wato_pprint_config,
        use_git=api_context.config.wato_use_git,
    )
    password = load_password(name)
    return ApiResponse(body=serialize_password(name, password), etag=password_etag(name, password))


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
