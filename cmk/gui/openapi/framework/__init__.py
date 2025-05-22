#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Versioned REST API Framework

These types and functions are used to define the versioned REST API of Checkmk.
Once all endpoints are migrated to the new framework, the old marshmallow-based code can be removed.
"""

from ._types import ApiContext, HeaderParam, PathParam, QueryParam, RawRequestData
from ._validation import EndpointValidator
from .api_config import APIConfig, APIVersion, DeprecationDetails
from .content_types import ContentTypeConverter
from .registry import VersionedEndpointRegistry
from .versioned_endpoint import (
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    HandlerFunction,
    VersionedEndpoint,
)

validate_endpoint_definition = EndpointValidator.validate_endpoint_definition

__all__ = [
    "APIConfig",
    "ApiContext",
    "APIVersion",
    "ContentTypeConverter",
    "DeprecationDetails",
    "EndpointBehavior",
    "EndpointDoc",
    "EndpointHandler",
    "EndpointMetadata",
    "EndpointPermissions",
    "HandlerFunction",
    "HeaderParam",
    "PathParam",
    "QueryParam",
    "RawRequestData",
    "validate_endpoint_definition",
    "VersionedEndpoint",
    "VersionedEndpointRegistry",
]
