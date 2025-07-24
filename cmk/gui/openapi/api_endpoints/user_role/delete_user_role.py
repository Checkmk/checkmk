#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.gui.config import active_config
from cmk.gui.openapi.api_endpoints.user_role.utils import RW_PERMISSIONS
from cmk.gui.openapi.framework import PathParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model.converter import TypedPlainValidator, UserRoleIdConverter
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.watolib.userroles import delete_role, RoleID

from .endpoint_family import USER_ROLE_FAMILY


def delete_user_role_v1(
    role_id: Annotated[
        RoleID,
        TypedPlainValidator(
            str,
            UserRoleIdConverter(permission_type="wato.edit").should_be_custom_and_should_exist,
        ),
        PathParam(
            description="An existing custom user role that you want to delete.",
            example="userx",
        ),
    ],
) -> None:
    """Delete a user role"""
    delete_role(RoleID(role_id), pprint_value=active_config.wato_pprint_config)


ENDPOINT_DELETE_USER_ROLE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("user_role", "{role_id}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=USER_ROLE_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=delete_user_role_v1)},
)
