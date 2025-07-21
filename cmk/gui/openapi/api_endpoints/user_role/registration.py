#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from .delete_user_role import ENDPOINT_DELETE_USER_ROLE
from .endpoint_family import USER_ROLE_FAMILY
from .list_user_roles import ENDPOINT_LIST_USER_ROLES
from .show_user_role import ENDPOINT_SHOW_USER_ROLE


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    *,
    ignore_duplicates: bool,
) -> None:
    endpoint_family_registry.register(
        USER_ROLE_FAMILY,
        ignore_duplicates=ignore_duplicates,
    )
    versioned_endpoint_registry.register(
        ENDPOINT_LIST_USER_ROLES,
        ignore_duplicates=ignore_duplicates,
    )
    versioned_endpoint_registry.register(
        ENDPOINT_SHOW_USER_ROLE,
        ignore_duplicates=ignore_duplicates,
    )
    versioned_endpoint_registry.register(
        ENDPOINT_DELETE_USER_ROLE,
        ignore_duplicates=ignore_duplicates,
    )
