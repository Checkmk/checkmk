#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Configuration entities / Notification Parameter

These endpoints can be used to manipulate notification parameter via the configuration
entity API, for more information see "Configuration entities" endpoints."""

from collections.abc import Mapping
from typing import Any

from cmk.gui.http import Response
from cmk.gui.openapi.endpoints.configuration_entity._common import (
    get_endpoint_decorator,
    list_endpoint_decorator,
    serve_configuration_entity,
    serve_configuration_entity_list,
)
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection

from cmk import fields
from cmk.shared_typing.configuration_entity import ConfigEntityType


class NotificationParamResponse(DomainObject):
    domainType = fields.Constant(
        ConfigEntityType.notification_parameter.value,
        description="The domain type of the object.",
    )


class NotificationParamResponseCollection(DomainObjectCollection):
    domainType = fields.Constant(
        ConfigEntityType.notification_parameter.value,
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(NotificationParamResponse),
        description="A list of notification parameter objects.",
    )


@list_endpoint_decorator(
    ConfigEntityType.notification_parameter, NotificationParamResponseCollection
)
def _list_notification_parameters(params: Mapping[str, Any]) -> Response:
    """List existing notification parameters"""
    return serve_configuration_entity_list(ConfigEntityType.notification_parameter, params)


@get_endpoint_decorator(ConfigEntityType.notification_parameter)
def _get_notification_parameter(params: Mapping[str, Any]) -> Response:
    """Get a notification parameter"""
    return serve_configuration_entity(ConfigEntityType.notification_parameter, params)


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(_list_notification_parameters, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(_get_notification_parameter, ignore_duplicates=ignore_duplicates)
