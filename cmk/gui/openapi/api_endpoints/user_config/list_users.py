#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.shared_endpoint_families.user_config import USER_CONFIG_FAMILY
from cmk.gui.userdb import load_users

from ._utils import PERMISSIONS, serialize_user
from .models.response_models import UserCollection


def list_users_v1() -> UserCollection:
    """Show all users"""
    user.need_permission("wato.users")
    return UserCollection(
        id="user_config",
        domainType="user_config",
        value=[
            serialize_user(user_id, user_spec)
            for user_id, user_spec in load_users(lock=False).items()
        ],
        links=[LinkModel.create("self", collection_href("user_config"))],
    )


ENDPOINT_LIST_USERS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("user_config"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=USER_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=list_users_v1)},
)
