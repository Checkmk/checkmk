#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from mimetypes import types_map

from polyfactory import Use
from polyfactory.factories import DataclassFactory, TypedDictFactory
from werkzeug.datastructures import Headers

from cmk.gui.openapi.framework import RawRequestData, registry, versioned_endpoint
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily


def _empty_handler() -> None:
    return None


class EndpointDocFactory(DataclassFactory[versioned_endpoint.EndpointDoc]):
    pass


class EndpointMetadataFactory(DataclassFactory[versioned_endpoint.EndpointMetadata]):
    pass


class EndpointPermissionsFactory(DataclassFactory[versioned_endpoint.EndpointPermissions]):
    required = None


class EndpointHandlerFactory(DataclassFactory[versioned_endpoint.EndpointHandler]):
    error_schemas = None

    @classmethod
    def handler(cls) -> versioned_endpoint.HandlerFunction:
        return _empty_handler


class VersionedEndpointFactory(DataclassFactory[versioned_endpoint.VersionedEndpoint]):
    metadata = EndpointMetadataFactory
    doc = EndpointDocFactory
    permissions = EndpointPermissionsFactory

    @classmethod
    def versions(cls) -> Mapping[APIVersion, versioned_endpoint.EndpointHandler]:
        return {
            APIVersion.V1: EndpointHandlerFactory.build(),
        }


class EndpointFamilyFactory(DataclassFactory[EndpointFamily]):
    pass


class EndpointBehaviorFactory(DataclassFactory[versioned_endpoint.EndpointBehavior]):
    pass


class EndpointDefinitionFactory(DataclassFactory[registry.EndpointDefinition]):
    metadata = EndpointMetadataFactory
    doc = EndpointDocFactory
    permissions = EndpointPermissionsFactory
    family = EndpointFamilyFactory
    handler = EndpointHandlerFactory
    behavior = EndpointBehaviorFactory


class RequestEndpointFactory(DataclassFactory[registry.RequestEndpoint]):
    permissions_required = None
    skip_locking = True

    @classmethod
    def handler(cls) -> versioned_endpoint.HandlerFunction:
        return _empty_handler

    @classmethod
    def content_type(cls) -> str:
        return cls.__random__.choice(list(types_map.values()))


class RawRequestDataFactory(TypedDictFactory[RawRequestData]):
    body = None
    path: Use[[], dict[str, str]] = Use(dict)
    query: Use[[], dict[str, list[str]]] = Use(dict)
    headers = Use(Headers)
