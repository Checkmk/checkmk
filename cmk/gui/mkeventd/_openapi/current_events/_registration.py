#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from .archive_events import ENDPOINT_ARCHIVE_CURRENT_EVENT
from .change_multiple_states import ENDPOINT_CHANGE_MULTIPLE_STATES_CURRENT_EVENTS
from .change_state import ENDPOINT_CHANGE_EVENT_STATE
from .endpoint_family import CURRENT_EVENTS_FAMILY
from .list_current_events import ENDPOINT_LIST_CURRENT_EVENTS
from .show_current_event import ENDPOINT_SHOW_CURRENT_EVENT
from .update_and_acknowledge import ENDPOINT_UPDATE_AND_ACK_EVENT
from .update_and_acknowledge_multiple import ENDPOINT_UPDATE_AND_ACK_MULTIPLE_EVENTS


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(CURRENT_EVENTS_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_CURRENT_EVENT)
    versioned_endpoint_registry.register(ENDPOINT_LIST_CURRENT_EVENTS)
    versioned_endpoint_registry.register(ENDPOINT_UPDATE_AND_ACK_EVENT)
    versioned_endpoint_registry.register(ENDPOINT_UPDATE_AND_ACK_MULTIPLE_EVENTS)
    versioned_endpoint_registry.register(ENDPOINT_CHANGE_EVENT_STATE)
    versioned_endpoint_registry.register(ENDPOINT_CHANGE_MULTIPLE_STATES_CURRENT_EVENTS)
    versioned_endpoint_registry.register(ENDPOINT_ARCHIVE_CURRENT_EVENT)
