#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Configuration entities

Configuration entities are single objects corresponding to configurations in Checkmk.
Which entities can be configured like this is defined by the configuration entity type.
"""

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any, assert_never, Sequence

from cmk.gui.form_specs.vue import shared_type_defs
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
from cmk.gui.watolib.configuration_entity import (
    ConfigEntityType,
    ConfigurationEntityDescription,
    EntityId,
    get_configuration_entity_data,
    get_list_of_configuration_entities,
    save_configuration_entity,
)

from cmk import fields

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


def _to_domain_type(entity_type: ConfigEntityType) -> type_defs.DomainType:
    match entity_type:
        case ConfigEntityType.NOTIFICATION_PARAMETER:
            return "notification_parameter"
        case other:
            assert_never(other)


def _serve_save_json(
    save_data: ConfigurationEntityDescription | Sequence[shared_type_defs.ValidationMessage],
) -> Response:
    if isinstance(save_data, ConfigurationEntityDescription):
        return serve_json(
            constructors.domain_object(
                domain_type="configuration_entity",
                identifier=save_data.ident,
                title=save_data.description,
                deletable=False,
                editable=False,
            )
        )

    # Since data is not necessarily a nested dictionary, we cannot build a perfect
    # error response so we approximate the structure
    error_fields: dict[str, Any] = {"data": {}}
    for val in save_data:
        node = error_fields["data"]
        for key in val.location:
            node = node.setdefault(key, {})
        node.setdefault("", []).append(val.message)

    return problem(
        422,
        "Validation error.",
        fields=FIELDS(error_fields),
        ext=EXT({"validation_errors": [asdict(val) for val in save_data]}),
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
def create_configuration_entity(params: Mapping[str, Any]) -> Response:
    """Create a configuration entity"""
    body = params["body"]
    entity_type = ConfigEntityType(body["entity_type"])
    entity_type_specifier = body["entity_type_specifier"]
    data = body["data"]

    return_data = save_configuration_entity(entity_type, entity_type_specifier, data, None)

    return _serve_save_json(return_data)


@Endpoint(
    constructors.domain_type_action_href("configuration_entity", "edit-single-entity"),
    ".../update",
    tag_group="Checkmk Internal",
    method="put",
    additional_status_codes=[422],
    request_schema=UpdateConfigurationEntity,
    response_schema=EditConfigurationEntityResponse,
)
def put_configuration_entity(params: Mapping[str, Any]) -> Response:
    """Update an existing configuration entity"""
    body = params["body"]
    entity_type = ConfigEntityType(body["entity_type"])
    entity_type_specifier = body["entity_type_specifier"]
    entity_id = EntityId(body["entity_id"])
    data = body["data"]

    return_data = save_configuration_entity(entity_type, entity_type_specifier, data, entity_id)

    return _serve_save_json(return_data)


@Endpoint(
    constructors.collection_href(
        _to_domain_type(ConfigEntityType.NOTIFICATION_PARAMETER), "{entity_type_specifier}"
    ),
    "cmk/list",
    tag_group="Checkmk Internal",
    path_params=[ENTITY_TYPE_SPECIFIER_FIELD],
    method="get",
    response_schema=response_schemas.DomainObjectCollection,
)
def list_configuration_entities(params: Mapping[str, Any]) -> Response:
    """List existing notification parameter"""
    entity_type_specifier = params["entity_type_specifier"]

    entity_descriptions = get_list_of_configuration_entities(
        ConfigEntityType.NOTIFICATION_PARAMETER, entity_type_specifier
    )

    return serve_json(
        constructors.collection_object(
            domain_type=_to_domain_type(ConfigEntityType.NOTIFICATION_PARAMETER),
            value=[
                constructors.domain_object(
                    domain_type=_to_domain_type(ConfigEntityType.NOTIFICATION_PARAMETER),
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
        _to_domain_type(ConfigEntityType.NOTIFICATION_PARAMETER), "{entity_id}"
    ),
    "cmk/show",
    tag_group="Checkmk Internal",
    path_params=[ENTITY_ID_FIELD],
    method="get",
    response_schema=response_schemas.DomainObject,
)
def get_configuration_entity(params: Mapping[str, Any]) -> Response:
    """Get a notification parameter"""
    entity_id = EntityId(params["entity_id"])

    data = get_configuration_entity_data(ConfigEntityType.NOTIFICATION_PARAMETER, entity_id)

    return serve_json(
        constructors.domain_object(
            domain_type=_to_domain_type(ConfigEntityType.NOTIFICATION_PARAMETER),
            identifier=entity_id,
            title="",
            extensions=dict(data),
            editable=False,
            deletable=False,
        )
    )


def register(endpoint_registry: EndpointRegistry) -> None:
    endpoint_registry.register(create_configuration_entity)
    endpoint_registry.register(put_configuration_entity)
    endpoint_registry.register(list_configuration_entities)
    endpoint_registry.register(get_configuration_entity)
