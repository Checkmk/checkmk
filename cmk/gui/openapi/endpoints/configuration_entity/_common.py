#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any, assert_never

from cmk.gui.http import Response
from cmk.gui.openapi.restful_objects import constructors, Endpoint, response_schemas, type_defs
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.watolib.configuration_entity.configuration_entity import (
    EntityId,
    get_configuration_entity,
    get_list_of_configuration_entities,
)

from cmk import fields
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


def to_domain_type(entity_type: ConfigEntityType) -> type_defs.DomainType:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return ConfigEntityType.notification_parameter.value
        case ConfigEntityType.folder:
            return ConfigEntityType.folder.value
        case other:
            assert_never(other)


def list_endpoint_decorator(
    entity_type: ConfigEntityType, response_schema: type[response_schemas.DomainObjectCollection]
) -> Endpoint:
    return Endpoint(
        constructors.collection_href(to_domain_type(entity_type), "{entity_type_specifier}"),
        "cmk/list",
        tag_group="Checkmk Internal",
        path_params=[ENTITY_TYPE_SPECIFIER_FIELD],
        method="get",
        response_schema=response_schema,
    )


def serve_configuration_entity_list(
    entity_type: ConfigEntityType, params: Mapping[str, Any]
) -> Response:
    entity_type_specifier = params["entity_type_specifier"]

    entity_descriptions = get_list_of_configuration_entities(entity_type, entity_type_specifier)

    return serve_json(
        constructors.collection_object(
            domain_type=to_domain_type(entity_type),
            value=[
                constructors.domain_object(
                    domain_type=to_domain_type(entity_type),
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


def get_endpoint_decorator(entity_type: ConfigEntityType) -> Endpoint:
    return Endpoint(
        constructors.object_href(to_domain_type(entity_type), "{entity_id}"),
        "cmk/show",
        tag_group="Checkmk Internal",
        path_params=[ENTITY_ID_FIELD],
        method="get",
        response_schema=response_schemas.DomainObject,
    )


def serve_configuration_entity(
    entity_type: ConfigEntityType, params: Mapping[str, Any]
) -> Response:
    entity_id = EntityId(params["entity_id"])

    try:
        entity = get_configuration_entity(entity_type, entity_id)
    except KeyError:
        return problem(
            404, title="Not found", detail=f"Configuration entity {entity_id} not found."
        )

    return serve_json(
        constructors.domain_object(
            domain_type=to_domain_type(entity_type),
            identifier=entity_id,
            title=entity.description,
            extensions=dict(entity.data),
            editable=False,
            deletable=False,
        )
    )
