#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import DATA_SOURCE_FAMILY
from .list_data_sources import ENDPOINT_LIST_DATA_SOURCES


def register_endpoints(
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    *,
    ignore_duplicates: bool = False,
) -> None:
    endpoint_family_registry.register(DATA_SOURCE_FAMILY, ignore_duplicates=ignore_duplicates)

    versioned_endpoint_registry.register(
        ENDPOINT_LIST_DATA_SOURCES, ignore_duplicates=ignore_duplicates
    )
