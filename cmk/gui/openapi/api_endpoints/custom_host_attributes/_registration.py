#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import CUSTOM_HOST_ATTR_FAMILY
from .create_custom_host_attr import ENDPOINT_CREATE_CUSTOM_HOST_ATTR
from .delete_custom_host_attr import ENDPOINT_DELETE_CUSTOM_HOST_ATTR
from .list_custom_host_attrs import ENDPOINT_LIST_CUSTOM_HOST_ATTRS
from .show_custom_host_attr import ENDPOINT_SHOW_CUSTOM_HOST_ATTR
from .update_custom_host_attr import ENDPOINT_UPDATE_CUSTOM_HOST_ATTR


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(CUSTOM_HOST_ATTR_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_LIST_CUSTOM_HOST_ATTRS)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_CUSTOM_HOST_ATTR)
    versioned_endpoint_registry.register(ENDPOINT_CREATE_CUSTOM_HOST_ATTR)
    versioned_endpoint_registry.register(ENDPOINT_UPDATE_CUSTOM_HOST_ATTR)
    versioned_endpoint_registry.register(ENDPOINT_DELETE_CUSTOM_HOST_ATTR)
