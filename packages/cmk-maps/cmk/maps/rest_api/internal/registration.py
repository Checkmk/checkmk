#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.maps.rest_api.internal.aggregations import (
    ENDPOINT_LIST_AGGREGATIONS,
    ENDPOINT_SHOW_AGGREGATION_STATES,
    ENDPOINT_SHOW_AGGREGATION_TREE,
)
from cmk.maps.rest_api.internal.backgrounds import (
    ENDPOINT_DELETE_BACKGROUND,
    ENDPOINT_UPLOAD_BACKGROUND,
)
from cmk.maps.rest_api.internal.cfg_import import ENDPOINT_PARSE_CFG
from cmk.maps.rest_api.internal.commands import ENDPOINT_RUN_COMMAND
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.form_schemas import (
    ENDPOINT_PARSE_FORM,
    ENDPOINT_SHOW_FORM_SCHEMA,
)
from cmk.maps.rest_api.internal.images import (
    ENDPOINT_DELETE_IMAGE,
    ENDPOINT_LIST_IMAGES,
    ENDPOINT_SHOW_IMAGE_USAGE,
    ENDPOINT_UPLOAD_IMAGE,
)
from cmk.maps.rest_api.internal.metrics import ENDPOINT_SHOW_METRIC_INFO
from cmk.maps.rest_api.internal.object_lookups import (
    ENDPOINT_LIST_DYNGROUP_MEMBERS,
    ENDPOINT_LIST_FOLDERS,
    ENDPOINT_LIST_GROUP_MEMBERS,
    ENDPOINT_LIST_SITES,
    ENDPOINT_SHOW_HOST_GEO,
    ENDPOINT_SHOW_PERF_METRICS,
)
from cmk.maps.rest_api.internal.settings import ENDPOINT_SHOW_AUTHORING_SETTINGS
from cmk.maps.rest_api.internal.tickets import ENDPOINT_SHOW_TICKET


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(MAPS_INTERNAL_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_HOST_GEO)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_PERF_METRICS)
    versioned_endpoint_registry.register(ENDPOINT_LIST_GROUP_MEMBERS)
    versioned_endpoint_registry.register(ENDPOINT_LIST_DYNGROUP_MEMBERS)
    versioned_endpoint_registry.register(ENDPOINT_LIST_FOLDERS)
    versioned_endpoint_registry.register(ENDPOINT_LIST_SITES)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_METRIC_INFO)
    versioned_endpoint_registry.register(ENDPOINT_LIST_AGGREGATIONS)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_AGGREGATION_TREE)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_AGGREGATION_STATES)
    versioned_endpoint_registry.register(ENDPOINT_LIST_IMAGES)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_IMAGE_USAGE)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_AUTHORING_SETTINGS)
    versioned_endpoint_registry.register(ENDPOINT_UPLOAD_IMAGE)
    versioned_endpoint_registry.register(ENDPOINT_DELETE_IMAGE)
    versioned_endpoint_registry.register(ENDPOINT_UPLOAD_BACKGROUND)
    versioned_endpoint_registry.register(ENDPOINT_DELETE_BACKGROUND)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_TICKET)
    versioned_endpoint_registry.register(ENDPOINT_RUN_COMMAND)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_FORM_SCHEMA)
    versioned_endpoint_registry.register(ENDPOINT_PARSE_FORM)
    versioned_endpoint_registry.register(ENDPOINT_PARSE_CFG)
