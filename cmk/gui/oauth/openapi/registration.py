#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from .endpoint_family import GUI_SESSION_FAMILY
from .identify_session import ENDPOINT_IDENTIFY_SESSION


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    *,
    ignore_duplicates: bool,
) -> None:
    endpoint_family_registry.register(GUI_SESSION_FAMILY, ignore_duplicates=ignore_duplicates)
    versioned_endpoint_registry.register(
        ENDPOINT_IDENTIFY_SESSION, ignore_duplicates=ignore_duplicates
    )
