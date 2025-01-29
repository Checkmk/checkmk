#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Configuration entities

Configuration entities are single objects corresponding to configurations in Checkmk.
Which entities can be configured like this is defined by the configuration entity type.
"""

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any, assert_never

from cmk.gui.form_specs.vue.form_spec_visitor import FormSpecValidationError
from cmk.gui.http import Response
from cmk.gui.openapi.endpoints.configuration_entity.request_schemas import (
    CreateConfigurationEntity,
    UpdateConfigurationEntity,
)
from cmk.gui.openapi.endpoints.configuration_entity.response_schemas import (
    EditConfigurationEntityResponse,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint, response_schemas, type_defs
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import EXT, FIELDS, problem, serve_json
from cmk.gui.watolib.configuration_entity.configuration_entity import (
    ConfigurationEntityDescription,
    EntityId,
    get_configuration_entity,
    get_configuration_entity_schema,
    get_list_of_configuration_entities,
    save_configuration_entity,
)

from cmk import fields
from cmk.shared_typing import vue_formspec_components as shared_type_defs
from cmk.shared_typing.configuration_entity import ConfigEntityType

ENTITY_ID_FIELD = {
    "entity_id": fields.String(
        required=True,
        description="Object id of the configuration entity",
        example="b43b060b-3b8c-41cf-8405-dddc6dd02575",
    )
}

ENTITY_TYPE_SPECIFIER_FIELD = {
    "entity_type_specifier": fields.String(
        required=True,
        description="Entity type specifier of the configuration entity",
        example="mail",
    )
}


ENTITY_TYPE = {
    "entity_type": fields.String(
        required=True,
        enum=[t.value for t in ConfigEntityType],
        description="Type of configuration entity",
        example=ConfigEntityType.notification_parameter.value,
    )
}


def _to_domain_type(entity_type: ConfigEntityType) -> type_defs.DomainType:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return "notification_parameter"
        case other:
            assert_never(other)


def _serve_validations(data: Sequence[shared_type_defs.ValidationMessage]) -> Response:
    # Since data is not necessarily a nested dictionary, we cannot build a perfect
    # error response so we approximate the structure
    error_fields: dict[str, Any] = {"data": {}}
    for val in data:
        node = error_fields["data"]
        for key in val.location:
            node = node.setdefault(key, {})
        node.setdefault("", []).append(val.message)

    return problem(
        422,
        "Validation error.",
        fields=FIELDS(error_fields),
        ext=EXT({"validation_errors": [asdict(val) for val in data]}),
    )


def _serve_entities(data: ConfigurationEntityDescription) -> Response:
    return serve_json(
        constructors.domain_object(
            domain_type="configuration_entity",
            identifier=data.ident,
            title=data.description,
            deletable=False,
            editable=False,
        )
    )


@Endpoint(
    constructors.collection_href("configuration_entity"),
    "cmk/create",
    tag_group="Checkmk Internal",
    method="post",
    additional_status_codes=[422],
    request_schema=CreateConfigurationEntity,
    response_schema=EditConfigurationEntityResponse,
)
def _create_configuration_entity(params: Mapping[str, Any]) -> Response:
    """Create a configuration entity"""
    body = params["body"]
    entity_type = ConfigEntityType(body["entity_type"])
    entity_type_specifier = body["entity_type_specifier"]
    data = body["data"]

    try:
        data = save_configuration_entity(entity_type, entity_type_specifier, data, None)
    except FormSpecValidationError as exc:
        return _serve_validations(exc.messages)

    return _serve_entities(data)


@Endpoint(
    constructors.domain_type_action_href("configuration_entity", "edit-single-entity"),
    ".../update",
    tag_group="Checkmk Internal",
    method="put",
    additional_status_codes=[422],
    request_schema=UpdateConfigurationEntity,
    response_schema=EditConfigurationEntityResponse,
)
def _update_configuration_entity(params: Mapping[str, Any]) -> Response:
    """Update an existing configuration entity"""
    body = params["body"]
    entity_type = ConfigEntityType(body["entity_type"])
    entity_type_specifier = body["entity_type_specifier"]
    entity_id = EntityId(body["entity_id"])
    data = body["data"]

    try:
        data = save_configuration_entity(entity_type, entity_type_specifier, data, entity_id)
    except FormSpecValidationError as exc:
        return _serve_validations(exc.messages)

    return _serve_entities(data)


@Endpoint(
    constructors.collection_href(
        _to_domain_type(ConfigEntityType.notification_parameter), "{entity_type_specifier}"
    ),
    "cmk/list",
    tag_group="Checkmk Internal",
    path_params=[ENTITY_TYPE_SPECIFIER_FIELD],
    method="get",
    response_schema=response_schemas.DomainObjectCollection,
)
def _list_configuration_entities(params: Mapping[str, Any]) -> Response:
    """List existing notification parameter"""
    entity_type_specifier = params["entity_type_specifier"]

    entity_descriptions = get_list_of_configuration_entities(
        ConfigEntityType.notification_parameter, entity_type_specifier
    )

    return serve_json(
        constructors.collection_object(
            domain_type=_to_domain_type(ConfigEntityType.notification_parameter),
            value=[
                constructors.domain_object(
                    domain_type=_to_domain_type(ConfigEntityType.notification_parameter),
                    identifier=entry.ident,
                    title=entry.description,
                    include_links=False,
                    editable=False,
                    deletable=False,
                )
                for entry in entity_descriptions
            ],
        )
    )


@Endpoint(
    constructors.object_href(
        _to_domain_type(ConfigEntityType.notification_parameter), "{entity_id}"
    ),
    "cmk/show",
    tag_group="Checkmk Internal",
    path_params=[ENTITY_ID_FIELD],
    method="get",
    response_schema=response_schemas.DomainObject,
)
def _get_configuration_entity(params: Mapping[str, Any]) -> Response:
    """Get a notification parameter"""
    entity_id = EntityId(params["entity_id"])

    try:
        entity = get_configuration_entity(ConfigEntityType.notification_parameter, entity_id)
    except KeyError:
        return problem(
            404, title="Not found", detail=f"Configuration entity {entity_id} not found."
        )

    return serve_json(
        constructors.domain_object(
            domain_type=_to_domain_type(ConfigEntityType.notification_parameter),
            identifier=entity_id,
            title=entity.description,
            extensions=dict(entity.data),
            editable=False,
            deletable=False,
        )
    )


@Endpoint(
    constructors.collection_href("form_spec", "{entity_type}"),
    "cmk/show",
    tag_group="Checkmk Internal",
    path_params=[ENTITY_TYPE],
    query_params=[ENTITY_TYPE_SPECIFIER_FIELD],
    method="get",
    response_schema=response_schemas.DomainObject,
)
def _get_configuration_entity_form_spec_schema(params: Mapping[str, Any]) -> Response:
    """Get a configuration entity form spec schema"""
    entity_type = ConfigEntityType(params["entity_type"])
    entity_type_specifier = params["entity_type_specifier"]

    schema, default_values = get_configuration_entity_schema(entity_type, entity_type_specifier)

    return serve_json(
        constructors.domain_object(
            domain_type="form_spec",
            identifier="",
            title="",
            extensions={"schema": asdict(schema), "default_values": default_values},
            editable=False,
            deletable=False,
        )
    )


def register(endpoint_registry: EndpointRegistry) -> None:
    endpoint_registry.register(_create_configuration_entity)
    endpoint_registry.register(_update_configuration_entity)
    endpoint_registry.register(_list_configuration_entities)
    endpoint_registry.register(_get_configuration_entity)
    endpoint_registry.register(_get_configuration_entity_form_spec_schema)
