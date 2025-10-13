#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.gui.pages import PageEndpoint, PageRegistry

from .api import register_endpoints
from .user_message import ajax_acknowledge_user_message, ajax_delete_user_message, PageUserMessage


def register(
    page_registry: PageRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    *,
    ignore_duplicate_endpoints: bool = False,
) -> None:
    page_registry.register(PageEndpoint("user_message", PageUserMessage))
    page_registry.register(PageEndpoint("ajax_delete_user_message", ajax_delete_user_message))
    page_registry.register(
        PageEndpoint("ajax_acknowledge_user_message", ajax_acknowledge_user_message)
    )
    register_endpoints(
        endpoint_family_registry,
        versioned_endpoint_registry,
        ignore_duplicates=ignore_duplicate_endpoints,
    )
