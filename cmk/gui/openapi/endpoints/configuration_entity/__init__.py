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
from typing import Any, Sequence

from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.http import Response
from cmk.gui.openapi.endpoints.configuration_entity.request_schemas import (
    CreateConfigurationEntity,
    UpdateConfigurationEntity,
)
from cmk.gui.openapi.endpoints.configuration_entity.response_schemas import (
    EditConfigurationEntityResponse,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import EXT, FIELDS, problem, serve_json
from cmk.gui.watolib.configuration_entity import (
    ConfigEntityType,
    ConfigurationEntityDescription,
    EntityId,
    save_configuration_entity,
)


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


def register(endpoint_registry: EndpointRegistry) -> None:
    endpoint_registry.register(create_configuration_entity)
    endpoint_registry.register(put_configuration_entity)
