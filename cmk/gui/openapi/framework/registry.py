#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass

from cmk.gui.http import HTTPMethod
from cmk.gui.openapi import endpoint_family_registry
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model.response import ApiErrorDataclass
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.type_defs import (
    AcceptFieldType,
    EndpointKey,
    ErrorStatusCodeInt,
    ETagBehaviour,
    StatusCodeInt,
    TagGroup,
)
from cmk.gui.openapi.restful_objects.utils import endpoint_ident
from cmk.gui.utils.permission_verification import BasePerm


@dataclass(frozen=True, slots=True)
class RequestEndpoint:
    handler: Callable  # TODO: change to HandlerFunction
    method: HTTPMethod
    accept: AcceptFieldType
    content_type: str
    etag: ETagBehaviour | None
    operation_id: str
    doc_group: TagGroup
    additional_status_codes: Sequence[StatusCodeInt]
    update_config_generation: bool
    permissions_required: BasePerm | None


@dataclass(slots=True, frozen=True)
class VersionedSpecEndpoint:
    operation_id: str
    path: str
    family: str
    doc_group: TagGroup
    doc_sort_index: int
    deprecated_werk_id: int | None
    handler: Callable
    error_schemas: Mapping[ErrorStatusCodeInt, type[ApiErrorDataclass]] | None
    status_descriptions: Mapping[StatusCodeInt, str] | None
    additional_status_codes: Sequence[StatusCodeInt] | None
    method: HTTPMethod
    content_type: str
    etag: ETagBehaviour | None
    permissions_required: BasePerm | None
    permissions_description: Mapping[str, str] | None
    accept: AcceptFieldType


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

    def request_endpoint(self) -> RequestEndpoint:
        """Representation of the endpoint with attributes needed to handle a request"""
        return RequestEndpoint(
            handler=self.handler.handler,
            method=self.metadata.method,
            accept=self.metadata.accept,
            content_type=self.metadata.content_type,
            etag=self.behavior.etag,
            operation_id=f"{self.metadata.family}.{self.handler.handler.__name__}",
            doc_group=self.doc.group,
            additional_status_codes=self.handler.additional_status_codes or [],
            update_config_generation=self.behavior.update_config_generation,
            permissions_required=self.permissions.required,
        )

    def spec_endpoint(self) -> VersionedSpecEndpoint:
        # TODO: separate models from other attributes
        return VersionedSpecEndpoint(
            operation_id=f"{self.metadata.family}.{self.handler.handler.__name__}",
            path=self.metadata.path,
            family=self.metadata.family,
            doc_group=self.doc.group,
            doc_sort_index=self.doc.sort_index,
            deprecated_werk_id=self.doc.sort_index,
            handler=self.handler.handler,
            error_schemas=self.handler.error_schemas,
            status_descriptions=self.handler.status_descriptions,
            additional_status_codes=self.handler.additional_status_codes,
            method=self.metadata.method,
            content_type=self.metadata.content_type,
            etag=self.behavior.etag,
            permissions_required=self.permissions.required,
            permissions_description=self.permissions.descriptions,
            accept=self.metadata.accept,
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
