#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.monitor.setup_folders import SetupFolderSource
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._acknowledge import ENDPOINT_ACKNOWLEDGE, ENDPOINT_REMOVE_ACKNOWLEDGEMENTS
from ._action_menu import ENDPOINT_GET_HOST_ACTION_MENU
from ._archive_events import ENDPOINT_ARCHIVE_EVENTS
from ._custom_notification import ENDPOINT_SEND_CUSTOM_NOTIFICATION
from ._events import ENDPOINT_GET_HOST_EVENTS
from ._fake_check_result import ENDPOINT_FAKE_CHECK_RESULT
from ._family import MONITOR_HOSTS_FAMILY
from ._host_overview import make_endpoint_get_host_overview
from ._list_hosts import make_endpoint_list_hosts
from ._modified_attributes import (
    ENDPOINT_RESET_MODIFIED_ATTRIBUTES,
    ENDPOINT_TOGGLE_ATTRIBUTE,
)
from ._reschedule import ENDPOINT_RESCHEDULE_CHECKS


def register_endpoints(
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    setup_folders: SetupFolderSource,
) -> None:
    endpoint_family_registry.register(MONITOR_HOSTS_FAMILY)

    versioned_endpoint_registry.register(make_endpoint_list_hosts(setup_folders))
    versioned_endpoint_registry.register(make_endpoint_get_host_overview(setup_folders))
    versioned_endpoint_registry.register(ENDPOINT_GET_HOST_ACTION_MENU)
    versioned_endpoint_registry.register(ENDPOINT_GET_HOST_EVENTS)
    versioned_endpoint_registry.register(ENDPOINT_RESCHEDULE_CHECKS)
    versioned_endpoint_registry.register(ENDPOINT_SEND_CUSTOM_NOTIFICATION)
    versioned_endpoint_registry.register(ENDPOINT_FAKE_CHECK_RESULT)
    versioned_endpoint_registry.register(ENDPOINT_TOGGLE_ATTRIBUTE)
    versioned_endpoint_registry.register(ENDPOINT_RESET_MODIFIED_ATTRIBUTES)
    versioned_endpoint_registry.register(ENDPOINT_ARCHIVE_EVENTS)
    versioned_endpoint_registry.register(ENDPOINT_ACKNOWLEDGE)
    versioned_endpoint_registry.register(ENDPOINT_REMOVE_ACKNOWLEDGEMENTS)
