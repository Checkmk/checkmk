#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.maps.rest_api.endpoint_family import MAPS_FAMILY

from .create_map import ENDPOINT_CREATE_MAP
from .delete_map import ENDPOINT_DELETE_MAP
from .list_maps import ENDPOINT_LIST_MAPS
from .show_map import ENDPOINT_SHOW_MAP
from .update_map import ENDPOINT_UPDATE_MAP


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(MAPS_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_LIST_MAPS)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_MAP)
    versioned_endpoint_registry.register(ENDPOINT_CREATE_MAP)
    versioned_endpoint_registry.register(ENDPOINT_UPDATE_MAP)
    versioned_endpoint_registry.register(ENDPOINT_DELETE_MAP)
