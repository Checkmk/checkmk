#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from pydantic import AfterValidator

from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.password.endpoint_family import PASSWORD_FAMILY
from cmk.gui.openapi.api_endpoints.password.models.request_models import (
    UpdatePassword,
)
from cmk.gui.openapi.api_endpoints.password.models.response_models import PasswordObject
from cmk.gui.openapi.api_endpoints.password.utils import RW_PERMISSIONS, serialize_password
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
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.watolib.passwords import load_password, load_password_to_modify, save_password


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
) -> PasswordObject:
    """Update a password"""
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")
    password_details = body.update(load_password_to_modify(name))
    save_password(
        name,
        password_details,
        new_password=False,
        user_id=user.id,
        pprint_value=api_context.config.wato_pprint_config,
        use_git=api_context.config.wato_use_git,
    )
    return serialize_password(name, load_password(name))


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
