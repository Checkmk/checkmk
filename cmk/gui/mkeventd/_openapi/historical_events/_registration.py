#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from .endpoint_family import HISTORICAL_EVENTS_FAMILY
from .list_historical_events import ENDPOINT_LIST_HISTORICAL_EVENTS
from .show_historical_event import ENDPOINT_SHOW_HISTORICAL_EVENT


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(HISTORICAL_EVENTS_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_HISTORICAL_EVENT)
    versioned_endpoint_registry.register(ENDPOINT_LIST_HISTORICAL_EVENTS)
