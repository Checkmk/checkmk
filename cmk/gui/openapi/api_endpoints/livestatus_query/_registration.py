#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import LIVESTATUS_QUERY_FAMILY
from .query_table import ENDPOINT_QUERY_TABLE


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    # The family must be registered before the endpoint (framework registry asserts it exists).
    endpoint_family_registry.register(LIVESTATUS_QUERY_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_QUERY_TABLE)
