#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, cast

from cmk.ccc.user import UserId
from cmk.crypto.password import PasswordPolicy
from cmk.gui.logged_in import user
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
from cmk.gui.openapi.shared_endpoint_families.user_config import USER_CONFIG_FAMILY
from cmk.gui.type_defs import UserSpec
from cmk.gui.userdb import get_user_attributes
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.users import create_user as wato_create_user
from cmk.gui.watolib.users import user_features_registry
from cmk.utils import paths

from ._utils import (
    api_to_internal_format,
    load_user,
    make_pending_changes,
    RW_PERMISSIONS,
    serialize_user,
    user_etag,
)
from .models.request_models import CreateUserModel
from .models.response_models import UserObject

_CREATE_PERMISSIONS = permissions.AllPerm(
    [
        *RW_PERMISSIONS.perms,
        permissions.Optional(permissions.Perm("wato.groups")),
    ]
)


def create_user_v1(api_context: ApiContext, body: CreateUserModel) -> ApiResponse[UserObject]:
    """Create a user

    You can pass custom attributes you defined directly in the top level JSON object of the request.
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    username = UserId(body.username)

    # The interface options must be set for a new user, but we restrict the setting through the API
    initial_attrs: dict[str, Any] = {"force_authuser": False}
    internal_attrs = api_to_internal_format(
        initial_attrs,
        body.to_internal_dict(),
        PasswordPolicy(
            api_context.config.password_policy.get("min_length"),
            api_context.config.password_policy.get("num_groups"),
            api_context.config.password_policy.get("wordlist_check", True),
            paths.wordlist_file,
        ),
        new_user=True,
    )
    wato_create_user(
        username,
        cast(UserSpec, internal_attrs),
        user_features_registry.features().sites,
        get_user_attributes(api_context.config.wato_user_attrs),
        api_context.config.user_connections,
        pending_changes=make_pending_changes(api_context),
        use_git=api_context.config.wato_use_git,
        acting_user=user,
        pprint_value=api_context.config.wato_pprint_config,
    )
    user_spec = load_user(username)
    return ApiResponse(
        status_code=200,
        body=serialize_user(username, user_spec),
        etag=user_etag(user_spec),
    )


ENDPOINT_CREATE_USER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("user_config"),
        link_relation="cmk/create",
        method="post",
    ),
    behavior=EndpointBehavior(etag="output"),
    permissions=EndpointPermissions(required=_CREATE_PERMISSIONS),
    doc=EndpointDoc(family=USER_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=create_user_v1)},
)
