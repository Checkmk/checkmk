#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Configuration entities / Rule form spec

These endpoints can be used to manipulate rules via the configuration entity
API, for more information see "Configuration entities" endpoints."""

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
from cmk.gui.openapi.restful_objects.response_schemas import (
    DomainObject,
    DomainObjectCollection,
)
from cmk.shared_typing.configuration_entity import ConfigEntityType


class RuleFormSpecResponse(DomainObject):
    domainType = fields.Constant(
        ConfigEntityType.rule_form_spec.value,
        description="The domain type of the object.",
    )


class RuleFormSpecResponseCollection(DomainObjectCollection):
    domainType = fields.Constant(
        ConfigEntityType.rule_form_spec.value,
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(RuleFormSpecResponse),
        description="A list of rules.",
    )


@list_endpoint_decorator(ConfigEntityType.rule_form_spec, RuleFormSpecResponseCollection)
def _list_rule_form_specs(params: Mapping[str, Any]) -> Response:
    """List existing rules"""
    return serve_configuration_entity_list(ConfigEntityType.rule_form_spec, params, user=user)


@get_endpoint_decorator(ConfigEntityType.rule_form_spec)
def _get_rule_form_spec(params: Mapping[str, Any]) -> Response:
    """Get a rule form spec parameter"""
    return serve_configuration_entity(ConfigEntityType.rule_form_spec, params, user)


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(_list_rule_form_specs, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(_get_rule_form_spec, ignore_duplicates=ignore_duplicates)
