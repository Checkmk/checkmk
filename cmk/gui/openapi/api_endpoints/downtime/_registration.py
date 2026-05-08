#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import DOWNTIME_FAMILY
from .create_host_downtime import ENDPOINT_CREATE_HOST_DOWNTIME
from .create_service_downtime import ENDPOINT_CREATE_SERVICE_DOWNTIME
from .delete_downtime import ENDPOINT_DELETE_DOWNTIME
from .modify_downtime import ENDPOINT_MODIFY_DOWNTIME
from .show_downtime import ENDPOINT_SHOW_DOWNTIME
from .show_downtimes import ENDPOINT_SHOW_DOWNTIMES


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(DOWNTIME_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_CREATE_HOST_DOWNTIME)
    versioned_endpoint_registry.register(ENDPOINT_CREATE_SERVICE_DOWNTIME)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_DOWNTIMES)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_DOWNTIME)
    versioned_endpoint_registry.register(ENDPOINT_DELETE_DOWNTIME)
    versioned_endpoint_registry.register(ENDPOINT_MODIFY_DOWNTIME)
