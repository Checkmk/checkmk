#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.hooks import register_builtin
from cmk.gui.monitor.command import DowntimeRecurrences, MonitorCommands
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.gui.pages import PageRegistry

from ._api._registration import register_endpoints
from ._legacy_view_link import show_host_services_link_button
from ._page_menu import HostMenus
from ._pages._registration import register_pages


def register(
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    page_registry: PageRegistry,
    command_registry: MonitorCommands,
    downtime_recurrences: DowntimeRecurrences,
    host_menus: HostMenus,
) -> None:
    register_endpoints(endpoint_family_registry, versioned_endpoint_registry)
    register_pages(page_registry, command_registry, downtime_recurrences, host_menus)
    register_builtin("experimental_view_button", show_host_services_link_button)
