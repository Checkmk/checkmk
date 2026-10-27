#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.monitor.setup_folders import SetupFolderSource
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._action_menu import ENDPOINT_GET_HOST_ACTION_MENU
from ._custom_notification import ENDPOINT_SEND_CUSTOM_NOTIFICATION
from ._events import ENDPOINT_GET_HOST_EVENTS
from ._family import MONITOR_HOSTS_FAMILY
from ._host_overview import make_endpoint_get_host_overview
from ._list_hosts import make_endpoint_list_hosts
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
