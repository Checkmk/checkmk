#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from .endpoint_family import HOST_AVAILABILITY_FAMILY, SERVICE_AVAILABILITY_FAMILY
from .list_host_availability import ENDPOINT_LIST_HOST_AVAILABILITY
from .list_service_availability import ENDPOINT_LIST_SERVICE_AVAILABILITY
from .show_host_availability import ENDPOINT_SHOW_HOST_AVAILABILITY
from .show_service_availability import ENDPOINT_SHOW_SERVICE_AVAILABILITY


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    *,
    ignore_duplicates: bool,
) -> None:
    endpoint_family_registry.register(HOST_AVAILABILITY_FAMILY, ignore_duplicates=ignore_duplicates)
    endpoint_family_registry.register(
        SERVICE_AVAILABILITY_FAMILY, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_LIST_HOST_AVAILABILITY, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_SHOW_HOST_AVAILABILITY, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_LIST_SERVICE_AVAILABILITY, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_SHOW_SERVICE_AVAILABILITY, ignore_duplicates=ignore_duplicates
    )
