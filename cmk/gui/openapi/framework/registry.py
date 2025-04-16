#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from dataclasses import dataclass

from cmk.gui.openapi import endpoint_family_registry
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.type_defs import EndpointKey
from cmk.gui.openapi.restful_objects.utils import endpoint_ident


@dataclass
class EndpointDefinition:
    metadata: EndpointMetadata
    permissions: EndpointPermissions
    doc: EndpointDoc
    handler: EndpointHandler
    behavior: EndpointBehavior
    removed_in_version: APIVersion | None

    @property
    def ident(self) -> str:
        return endpoint_ident(
            method=self.metadata.method,
            route_path=self.metadata.path,
            content_type=self.metadata.content_type,
        )


class VersionedEndpointRegistry:
    """Registry for versioned REST API endpoints"""

    def __init__(self):
        self._versions: dict[APIVersion, dict[EndpointKey, EndpointDefinition]] = dict()

    # TODO: potentially have to introduce a lookup function
    def register(self, endpoint: VersionedEndpoint) -> None:
        """Register a versioned endpoint

        Registers the endpoint with all its handlers for different API versions.
        """

        endpoint_family = endpoint_family_registry.get(endpoint.metadata.family)
        assert endpoint_family is not None
        endpoint_key = (endpoint_family.name, endpoint.metadata.link_relation)

        for version, handler in endpoint.versions.items():
            version_endpoints = self._versions.setdefault(version, dict())

            if endpoint_key in version_endpoints:
                raise RuntimeError(
                    f"Endpoint with key {endpoint_key}, already has handlers for version {version}"
                )

            version_endpoints[endpoint_key] = EndpointDefinition(
                metadata=endpoint.metadata,
                permissions=endpoint.permissions,
                doc=endpoint.doc,
                handler=handler,
                behavior=endpoint.behavior,
                removed_in_version=endpoint.removed_in_version,
            )

    def specified_endpoints(self, version: APIVersion) -> Iterator[EndpointDefinition]:
        """Iterate over all endpoints specified for a given API version"""
        for _endpoint_key, endpoint in self._versions.get(version, dict()).items():
            yield endpoint


versioned_endpoint_registry = VersionedEndpointRegistry()
