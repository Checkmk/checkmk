#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.hooks import request_memoize
from cmk.gui.openapi.framework.api_config import APIConfig, APIVersion
from cmk.gui.openapi.framework.registry import EndpointDefinition, versioned_endpoint_registry
from cmk.gui.openapi.restful_objects import Endpoint
from cmk.gui.openapi.restful_objects.registry import endpoint_registry as legacy_endpoint_registry

type ExcludedEndpoints = set[str]
type ExcludedEndpointsByVersion = dict[APIVersion, ExcludedEndpoints]
type DiscoveredEndpoints = dict[str, Endpoint | EndpointDefinition]
type DiscoveredEndpointsByVersion = dict[APIVersion, DiscoveredEndpoints]


def discover_endpoints(version: APIVersion) -> DiscoveredEndpoints:
    discovered_endpoints, _ = _discover_endpoints(version)
    return discovered_endpoints


@request_memoize()
def _discover_endpoints(
    version: APIVersion,
) -> tuple[
    DiscoveredEndpoints,
    ExcludedEndpointsByVersion,
]:
    """
    Recursively discovers API endpoints for a given version. Each version is built on top
    of the previous one by adding new endpoints and excluding deprecated ones.

    Args:
        version: Target API version

    Returns:
        Tuple of discovered endpoints for the requested version dictionary and
        future excluded endpoints by version dictionary
    """

    try:
        discovered_endpoints, excluded_endpoints = _discover_endpoints(
            APIConfig.get_previous_released_version(target_version=version)
        )

    except ValueError:
        # No previous version available, so we start with empty dictionaries
        discovered_endpoints = {}
        excluded_endpoints = {}

    # Remove excluded endpoints (if any)
    if version in excluded_endpoints:
        for endpoint_key in excluded_endpoints[version]:
            if endpoint_key in discovered_endpoints:
                del discovered_endpoints[endpoint_key]

        del excluded_endpoints[version]

    def add_removed_in_version(version: APIVersion, endpoint_ident: str) -> None:
        if version not in excluded_endpoints:
            excluded_endpoints[version] = set()
        excluded_endpoints[version].add(endpoint_ident)

    if version == APIVersion.V1:
        legacy_endpoint: Endpoint
        for legacy_endpoint in legacy_endpoint_registry:
            discovered_endpoints[legacy_endpoint.ident] = legacy_endpoint

            if removed_in_version := legacy_endpoint.removed_in_version:
                add_removed_in_version(removed_in_version, legacy_endpoint.ident)

    versioned_endpoint: EndpointDefinition
    for versioned_endpoint in versioned_endpoint_registry.specified_endpoints(version):
        discovered_endpoints[versioned_endpoint.ident] = versioned_endpoint

        if removed_in_version := versioned_endpoint.removed_in_version:
            add_removed_in_version(removed_in_version, versioned_endpoint.ident)

    return discovered_endpoints, excluded_endpoints
