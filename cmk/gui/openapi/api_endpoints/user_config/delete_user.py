#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.ccc.user import UserId
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.shared_endpoint_families.user_config import USER_CONFIG_FAMILY
from cmk.gui.userdb import get_user_attributes
from cmk.gui.watolib.users import delete_users, user_features_registry

from ._utils import make_pending_changes, RW_PERMISSIONS, username_should_exist


def delete_user_v1(
    api_context: ApiContext,
    username: Annotated[
        Annotated[UserId, TypedPlainValidator(str, username_should_exist)],
        PathParam(description="An unique username for the user", example="cmkuser"),
    ],
) -> None:
    """Delete a user"""
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    delete_users(
        [username],
        user_features_registry.features().sites,
        user_attributes=get_user_attributes(api_context.config.wato_user_attrs),
        user_connections=api_context.config.user_connections,
        pending_changes=make_pending_changes(api_context),
        use_git=api_context.config.wato_use_git,
        acting_user=user,
        pprint_value=api_context.config.wato_pprint_config,
    )


ENDPOINT_DELETE_USER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("user_config", "{username}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=USER_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=delete_user_v1)},
)
