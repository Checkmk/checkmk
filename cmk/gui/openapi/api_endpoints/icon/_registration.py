#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import ICON_FAMILY
from .list_icon_categories import ENDPOINT_LIST_ICON_CATEGORIES
from .list_icon_emblems import ENDPOINT_LIST_ICON_EMBLEMS
from .list_icons import ENDPOINT_LIST_ICONS


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    *,
    ignore_duplicates: bool,
) -> None:
    endpoint_family_registry.register(ICON_FAMILY, ignore_duplicates=ignore_duplicates)
    versioned_endpoint_registry.register(
        ENDPOINT_LIST_ICON_CATEGORIES, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_LIST_ICON_EMBLEMS, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(ENDPOINT_LIST_ICONS, ignore_duplicates=ignore_duplicates)
