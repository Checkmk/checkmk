#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import DASHBOARD_FAMILY
from .create_dashboard import ENDPOINT_CREATE_DASHBOARD
from .delete_dashboard import ENDPOINT_DELETE_DASHBOARD
from .edit_dashboard import ENDPOINT_EDIT_DASHBOARD
from .list_dashboards import ENDPOINT_LIST_DASHBOARDS
from .show_dashboard import ENDPOINT_SHOW_DASHBOARD


def register_endpoints(
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    *,
    ignore_duplicates: bool = False,
) -> None:
    endpoint_family_registry.register(DASHBOARD_FAMILY, ignore_duplicates=ignore_duplicates)

    versioned_endpoint_registry.register(
        ENDPOINT_CREATE_DASHBOARD, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_DELETE_DASHBOARD, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_EDIT_DASHBOARD, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_LIST_DASHBOARDS, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_SHOW_DASHBOARD, ignore_duplicates=ignore_duplicates
    )
