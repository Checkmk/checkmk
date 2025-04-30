#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Mapping

from polyfactory.factories import DataclassFactory

from cmk.gui.openapi.framework import versioned_endpoint
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily


class EndpointDocFactory(DataclassFactory[versioned_endpoint.EndpointDoc]):
    pass


class EndpointMetadataFactory(DataclassFactory[versioned_endpoint.EndpointMetadata]):
    pass


class EndpointPermissionsFactory(DataclassFactory[versioned_endpoint.EndpointPermissions]):
    required = None


class EndpointHandlerFactory(DataclassFactory[versioned_endpoint.EndpointHandler]):
    error_schemas = None

    @classmethod
    def handler(cls) -> Callable:
        def dummy_handler() -> None:
            return None

        return dummy_handler


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
