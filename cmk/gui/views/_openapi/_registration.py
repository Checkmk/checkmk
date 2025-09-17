#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import VIEW_FAMILY
from .list_views import ENDPOINT_LIST_VIEWS


def register_endpoints(
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    *,
    ignore_duplicates: bool = False,
) -> None:
    endpoint_family_registry.register(VIEW_FAMILY, ignore_duplicates=ignore_duplicates)

    versioned_endpoint_registry.register(ENDPOINT_LIST_VIEWS, ignore_duplicates=ignore_duplicates)
