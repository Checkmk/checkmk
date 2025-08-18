#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from .create_site_connection import ENDPOINT_CREATE_SITE_CONNECTION
from .delete_site_connection import ENDPOINT_DELETE_SITE_CONNECTION
from .edit_site_connection import ENDPOINT_EDIT_SITE_CONNECTION
from .endpoint_family import SITE_MANAGEMENT_FAMILY
from .list_site_connections import ENDPOINT_LIST_SITE_CONNECTIONS
from .show_site_connection import ENDPOINT_SHOW_SITE_CONNECTION
from .site_login import ENDPOINT_SITE_CONNECTION_LOGIN
from .site_logout import ENDPOINT_SITE_CONNECTION_LOGOUT


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    *,
    ignore_duplicates: bool,
) -> None:
    endpoint_family_registry.register(
        SITE_MANAGEMENT_FAMILY,
        ignore_duplicates=ignore_duplicates,
    )
    versioned_endpoint_registry.register(
        ENDPOINT_LIST_SITE_CONNECTIONS,
        ignore_duplicates=ignore_duplicates,
    )
    versioned_endpoint_registry.register(
        ENDPOINT_SHOW_SITE_CONNECTION,
        ignore_duplicates=ignore_duplicates,
    )
    versioned_endpoint_registry.register(
        ENDPOINT_DELETE_SITE_CONNECTION,
        ignore_duplicates=ignore_duplicates,
    )
    versioned_endpoint_registry.register(
        ENDPOINT_SITE_CONNECTION_LOGIN,
        ignore_duplicates=ignore_duplicates,
    )
    versioned_endpoint_registry.register(
        ENDPOINT_SITE_CONNECTION_LOGOUT,
        ignore_duplicates=ignore_duplicates,
    )
    versioned_endpoint_registry.register(
        ENDPOINT_CREATE_SITE_CONNECTION,
        ignore_duplicates=ignore_duplicates,
    )
    versioned_endpoint_registry.register(
        ENDPOINT_EDIT_SITE_CONNECTION,
        ignore_duplicates=ignore_duplicates,
    )
