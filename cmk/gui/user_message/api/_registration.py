#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import USER_MESSAGE_FAMILY
from .acknowledge_message import ENDPOINT_ACKNOWLEDGE_MESSAGE
from .delete_user_message import ENDPOINT_DELETE_MESSAGE


def register_endpoints(
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    *,
    ignore_duplicates: bool = False,
) -> None:
    endpoint_family_registry.register(USER_MESSAGE_FAMILY, ignore_duplicates=ignore_duplicates)

    versioned_endpoint_registry.register(
        ENDPOINT_ACKNOWLEDGE_MESSAGE, ignore_duplicates=ignore_duplicates
    )
    versioned_endpoint_registry.register(
        ENDPOINT_DELETE_MESSAGE, ignore_duplicates=ignore_duplicates
    )
