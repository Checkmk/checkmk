#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, cast

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
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.shared_endpoint_families.user_config import USER_CONFIG_FAMILY
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.type_defs import UserSpec
from cmk.gui.userdb import get_user_attributes, locked_attributes
from cmk.gui.watolib.users import edit_user as wato_edit_user
from cmk.gui.watolib.users import user_features_registry
from cmk.utils import paths

from ._utils import (
    api_to_internal_format,
    identify_modified_attrs,
    load_user,
    make_pending_changes,
    RW_PERMISSIONS,
    serialize_user,
    user_etag,
    username_should_exist,
)
from .models.request_models import UpdateUserModel
from .models.response_models import UserObject


def edit_user_v1(
    api_context: ApiContext,
    username: Annotated[
        Annotated[UserId, TypedPlainValidator(str, username_should_exist)],
        PathParam(description="An unique username for the user", example="cmkuser"),
    ],
    body: UpdateUserModel,
) -> ApiResponse[UserObject]:
    """Edit a user

    You can pass custom attributes you defined directly in the top level JSON object of the request.
    """
    # last_pw_change & serial must be changed manually if edit happens
    current_attrs = load_user(username)
    if api_context.etag.enabled:
        api_context.etag.verify(user_etag(current_attrs))

    api_configurations = body.to_internal_dict()
    if api_configurations.get("auth_option", {}).get("auth_type") in (
        "password",
        "automation",
        "remove",
    ) and is_distributed_setup_remote_site(api_context.config.sites):
        raise ProblemException(
            status=403,
            title="Not allowed on remote site",
            detail="Changing user credentials is not permitted on remote sites.",
        )

    internal_attrs = api_to_internal_format(
        dict(current_attrs),
        api_configurations,
        PasswordPolicy(
            api_context.config.password_policy.get("min_length"),
            api_context.config.password_policy.get("num_groups"),
            api_context.config.password_policy.get("wordlist_check", True),
            paths.wordlist_file,
        ),
    )

    user_attributes = get_user_attributes(api_context.config.wato_user_attrs)
    if connector_id := internal_attrs.get("connector"):
        user_locked_attributes = set(locked_attributes(connector_id, user_attributes))
        if user_locked_attributes:
            modified_attrs = identify_modified_attrs(current_attrs, internal_attrs)
            locked_changes = user_locked_attributes.intersection(modified_attrs)
            if locked_changes:
                raise ProblemException(
                    status=403,
                    title="Attempt to modify locked attributes set by connector",
                    detail=f"Request attempts to modify the following locked attributes: {', '.join(locked_changes)}",
                )

    wato_edit_user(
        username,
        cast(UserSpec, internal_attrs),
        user_features_registry.features().sites,
        user_attributes,
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


ENDPOINT_EDIT_USER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("user_config", "{username}"),
        link_relation=".../update",
        method="put",
    ),
    behavior=EndpointBehavior(etag="both"),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=USER_CONFIG_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(handler=edit_user_v1, additional_status_codes=[403]),
    },
)
