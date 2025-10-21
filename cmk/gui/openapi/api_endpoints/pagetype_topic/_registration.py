#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import PAGETYPE_TOPIC_FAMILY
from .list_topics import ENDPOINT_LIST_TOPICS


def register(
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    *,
    ignore_duplicates: bool,
) -> None:
    endpoint_family_registry.register(PAGETYPE_TOPIC_FAMILY, ignore_duplicates=ignore_duplicates)

    versioned_endpoint_registry.register(ENDPOINT_LIST_TOPICS, ignore_duplicates=ignore_duplicates)
