#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._api._registration import register_endpoints


def register(
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
) -> None:
    register_endpoints(endpoint_family_registry, versioned_endpoint_registry)
