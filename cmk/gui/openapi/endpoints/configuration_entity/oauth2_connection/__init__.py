#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Configuration entities / OAuth2 connections API endpoints.

This module defines the API endpoints for managing OAuth2 configuration entities
within the Checkmk monitoring system. It includes functionality to list OAuth2
connections and integrates with the OpenAPI specification for documentation and
client generation.
"""

# mypy: disable-error-code="mutable-override"

from collections.abc import Mapping
from typing import Any

from cmk import fields
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.configuration_entity._common import (
    get_endpoint_decorator,
    list_endpoint_decorator,
    serve_configuration_entity,
    serve_configuration_entity_list,
)
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection
from cmk.shared_typing.configuration_entity import ConfigEntityType


class Oauth2ConnectionResponse(DomainObject):
    domainType = fields.Constant(
        ConfigEntityType.oauth2_connection.value,
        description="The domain type of the object.",
    )


class Oauth2ConnectionResponseCollection(DomainObjectCollection):
    domainType = fields.Constant(
        ConfigEntityType.oauth2_connection.value,
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(Oauth2ConnectionResponse),
        description="A list of OAuth2 configuration entities.",
    )


@list_endpoint_decorator(ConfigEntityType.oauth2_connection, Oauth2ConnectionResponseCollection)
def _list_oauth2_connections(params: Mapping[str, Any]) -> Response:
    """List OAuth2 configuration entities."""
    return serve_configuration_entity_list(ConfigEntityType.oauth2_connection, params, user=user)


@get_endpoint_decorator(ConfigEntityType.oauth2_connection)
def _get_oauth2_connection(params: Mapping[str, Any]) -> Response:
    """Get an OAuth2 connection"""
    return serve_configuration_entity(ConfigEntityType.oauth2_connection, params, user)


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(_list_oauth2_connections, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(_get_oauth2_connection, ignore_duplicates=ignore_duplicates)
