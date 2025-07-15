#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass

from cmk.ccc.version import Edition

from cmk.gui.http import HTTPMethod
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model.response import ApiErrorDataclass
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    HandlerFunction,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.endpoint_family import endpoint_family_registry, EndpointFamily
from cmk.gui.openapi.restful_objects.type_defs import (
    AcceptFieldType,
    EndpointKey,
    ErrorStatusCodeInt,
    ETagBehaviour,
    LinkRelation,
    StatusCodeInt,
    TagGroup,
)
from cmk.gui.openapi.restful_objects.utils import endpoint_ident, format_to_routing_path
from cmk.gui.utils.permission_verification import BasePerm


@dataclass(frozen=True, slots=True)
class RequestEndpoint:
    handler: HandlerFunction
    method: HTTPMethod
    accept: AcceptFieldType
    content_type: str | None
    etag: ETagBehaviour | None
    operation_id: str
    doc_group: TagGroup
    additional_status_codes: Sequence[StatusCodeInt]
    update_config_generation: bool
    skip_locking: bool
    permissions_required: BasePerm | None


@dataclass(slots=True, frozen=True)
class VersionedSpecEndpoint:
    operation_id: str
    path: str
    family: str
    doc_group: TagGroup
    doc_sort_index: int
    doc_supported_editions: set[Edition] | None
    deprecated_werk_id: int | None
    handler: Callable
    error_schemas: Mapping[ErrorStatusCodeInt, type[ApiErrorDataclass]] | None
    status_descriptions: Mapping[StatusCodeInt, str] | None
    additional_status_codes: Sequence[StatusCodeInt] | None
    method: HTTPMethod
    content_type: str | None
    etag: ETagBehaviour | None
    permissions_required: BasePerm | None
    permissions_description: Mapping[str, str] | None
    accept: AcceptFieldType


@dataclass
class EndpointDefinition:
    metadata: EndpointMetadata
    permissions: EndpointPermissions
    doc: EndpointDoc
    family: EndpointFamily
    handler: EndpointHandler
    behavior: EndpointBehavior
    removed_in_version: APIVersion | None

    @property
    def ident(self) -> str:
        # this must be consistent with the legacy endpoints, so the overwriting works correctly
        return endpoint_ident(
            method=self.metadata.method,
            route_path=format_to_routing_path(self.metadata.path),
            content_type=self.metadata.content_type,
        )

    @property
    def doc_group(self) -> TagGroup:
        return self.doc.group or self.family.doc_group

    def request_endpoint(self) -> RequestEndpoint:
        """Representation of the endpoint with attributes needed to handle a request"""
        return RequestEndpoint(
            handler=self.handler.handler,
            method=self.metadata.method,
            accept=self.metadata.accept,
            content_type=self.metadata.content_type,
            etag=self.behavior.etag,
            operation_id=f"{self.doc.family}.{self.handler.handler.__name__}",
            doc_group=self.doc_group,
            additional_status_codes=self.handler.additional_status_codes or [],
            update_config_generation=self.behavior.update_config_generation,
            skip_locking=self.behavior.skip_locking,
            permissions_required=self.permissions.required,
        )

    def spec_endpoint(self) -> VersionedSpecEndpoint:
        # TODO: separate models from other attributes
        return VersionedSpecEndpoint(
            operation_id=f"{self.doc.family}.{self.handler.handler.__name__}",
            path=self.metadata.path,
            family=self.doc.family,
            doc_group=self.doc_group,
            doc_sort_index=self.doc.sort_index,
            doc_supported_editions=self.doc.supported_editions,
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

    @staticmethod
    def create_endpoint_definition(
        endpoint: VersionedEndpoint, endpoint_family: EndpointFamily, handler: EndpointHandler
    ) -> EndpointDefinition:
        return EndpointDefinition(
            metadata=endpoint.metadata,
            permissions=endpoint.permissions,
            doc=endpoint.doc,
            family=endpoint_family,
            handler=handler,
            behavior=endpoint.behavior,
            removed_in_version=endpoint.removed_in_version,
        )

    @staticmethod
    def endpoint_key(family_name: str, link_relation: LinkRelation) -> tuple[str, LinkRelation]:
        return family_name, link_relation

    # TODO: potentially have to introduce a lookup function
    def register(self, endpoint: VersionedEndpoint, *, ignore_duplicates: bool) -> None:
        """Register a versioned endpoint

        Registers the endpoint with all its handlers for different API versions.
        """

        endpoint_family = endpoint_family_registry.get(endpoint.doc.family)
        assert endpoint_family is not None
        endpoint_key_ = self.endpoint_key(endpoint_family.name, endpoint.metadata.link_relation)

        for version, handler in endpoint.versions.items():
            version_endpoints = self._versions.setdefault(version, dict())

            if endpoint_key_ in version_endpoints:
                if ignore_duplicates:
                    continue

                raise RuntimeError(
                    f"Endpoint with key {endpoint_key_}, already has handlers for version {version}"
                )

            version_endpoints[endpoint_key_] = self.create_endpoint_definition(
                endpoint=endpoint,
                endpoint_family=endpoint_family,
                handler=handler,
            )

    def specified_endpoints(self, version: APIVersion) -> Iterator[EndpointDefinition]:
        """Iterate over all endpoints specified for a given API version"""
        for _endpoint_key, endpoint in self._versions.get(version, dict()).items():
            yield endpoint

    def __iter__(self) -> Iterator[EndpointDefinition]:
        """Iterate over all endpoints registered in the registry"""
        for version_endpoints in self._versions.values():
            yield from version_endpoints.values()


versioned_endpoint_registry = VersionedEndpointRegistry()
