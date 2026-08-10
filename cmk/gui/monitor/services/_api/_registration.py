#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import MONITOR_SERVICES_FAMILY
from ._list_host_services import ENDPOINT_LIST_HOST_SERVICES
from ._reschedule import ENDPOINT_RESCHEDULE_CHECKS
from ._service_overview import ENDPOINT_GET_SERVICE_OVERVIEW


def register_endpoints(
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
) -> None:
    endpoint_family_registry.register(MONITOR_SERVICES_FAMILY)

    versioned_endpoint_registry.register(ENDPOINT_LIST_HOST_SERVICES)
    versioned_endpoint_registry.register(ENDPOINT_GET_SERVICE_OVERVIEW)
    versioned_endpoint_registry.register(ENDPOINT_RESCHEDULE_CHECKS)
