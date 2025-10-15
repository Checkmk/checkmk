#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import DASHBOARD_FAMILY
from .clone_relative_dashboard import ENDPOINT_CLONE_AS_RELATIVE_GRID_DASHBOARD
from .compute_widget_attributes import ENDPOINT_COMPUTE_WIDGET_ATTRIBUTES
from .create_relative_grid_dashboard import ENDPOINT_CREATE_RELATIVE_GRID_DASHBOARD
from .delete_dashboard import ENDPOINT_DELETE_DASHBOARD
from .edit_relative_grid_dashboard import ENDPOINT_EDIT_RELATIVE_GRID_DASHBOARD
from .list_dashboard_metadata import ENDPOINT_LIST_DASHBOARD_METADATA
from .show_dashboard_constraints import ENDPOINT_SHOW_DASHBOARD_CONSTANTS
from .show_relative_grid_dashboard import ENDPOINT_SHOW_RELATIVE_GRID_DASHBOARD


def register_endpoints(
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    *,
    ignore_duplicates: bool = False,
) -> None:
    endpoint_family_registry.register(DASHBOARD_FAMILY, ignore_duplicates=ignore_duplicates)

    versioned_endpoint_registry.register(
        ENDPOINT_CREATE_RELATIVE_GRID_DASHBOARD, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_DELETE_DASHBOARD, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_EDIT_RELATIVE_GRID_DASHBOARD, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_SHOW_DASHBOARD_CONSTANTS, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_SHOW_RELATIVE_GRID_DASHBOARD, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_COMPUTE_WIDGET_ATTRIBUTES, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_LIST_DASHBOARD_METADATA, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_CLONE_AS_RELATIVE_GRID_DASHBOARD, ignore_duplicates=ignore_duplicates
    )
