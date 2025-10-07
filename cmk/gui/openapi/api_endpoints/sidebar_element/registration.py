#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from .endpoint_family import SIDEBAR_ELEMENT_FAMILY
from .list_sidebar_element import ENDPOINT_LIST_SIDEBAR_ELEMENT


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    *,
    ignore_duplicates: bool,
) -> None:
    endpoint_family_registry.register(SIDEBAR_ELEMENT_FAMILY, ignore_duplicates=ignore_duplicates)
    versioned_endpoint_registry.register(
        ENDPOINT_LIST_SIDEBAR_ELEMENT,
        ignore_duplicates=ignore_duplicates,
    )
