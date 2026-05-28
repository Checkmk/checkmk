#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import SERVICE_DISCOVERY_FAMILY
from .execute_bulk_discovery import ENDPOINT_EXECUTE_BULK_DISCOVERY
from .execute_service_discovery import ENDPOINT_EXECUTE_SERVICE_DISCOVERY
from .show_service_discovery_result import ENDPOINT_SHOW_SERVICE_DISCOVERY_RESULT
from .show_service_discovery_run import ENDPOINT_SHOW_SERVICE_DISCOVERY_RUN
from .update_service_phase import ENDPOINT_UPDATE_SERVICE_PHASE
from .wait_for_service_discovery_completion import ENDPOINT_WAIT_FOR_SERVICE_DISCOVERY_COMPLETION


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(SERVICE_DISCOVERY_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_SERVICE_DISCOVERY_RESULT)
    versioned_endpoint_registry.register(ENDPOINT_UPDATE_SERVICE_PHASE)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_SERVICE_DISCOVERY_RUN)
    versioned_endpoint_registry.register(ENDPOINT_WAIT_FOR_SERVICE_DISCOVERY_COMPLETION)
    versioned_endpoint_registry.register(ENDPOINT_EXECUTE_SERVICE_DISCOVERY)
    versioned_endpoint_registry.register(ENDPOINT_EXECUTE_BULK_DISCOVERY)
