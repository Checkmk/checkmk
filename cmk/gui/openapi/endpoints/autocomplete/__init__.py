#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Autocomplete (internal)

This provides access to autocomplete functionality. This currently is mostly used
internally by the Grafana's data source plug-in and relies on data sent by it that
is not fully documented and specified yet.
"""

from collections.abc import Mapping
from typing import Any

from cmk.ccc.version import Edition

from cmk.gui.config import active_config
from cmk.gui.http import Response
from cmk.gui.openapi.endpoints.autocomplete.request_schemas import RequestSchema
from cmk.gui.openapi.endpoints.autocomplete.response_schemas import ResponseSchema
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.valuespec import autocompleter_registry

from cmk import fields

AUTOCOMPLETE_ID = {
    "autocomplete_id": fields.String(
        description="The id of the autocompleter",
        example="tag_groups",
        required=False,
    )
}


@Endpoint(
    constructors.object_href("autocomplete", "{autocomplete_id}"),
    "cmk/show",
    method="post",
    tag_group="Checkmk Internal",
    path_params=[AUTOCOMPLETE_ID],
    request_schema=RequestSchema,
    response_schema=ResponseSchema,
    update_config_generation=False,
    supported_editions={Edition.CRE, Edition.CEE, Edition.CCE, Edition.CME},
)
def show(params: Mapping[str, Any]) -> Response:
    """
    Call the autocompleter specified in the url
    """

    body = params["body"]
    value = body.get("value", "")
    parameters = body.get("parameters", {})
    autocompleter = params["autocomplete_id"]
    internal_autocompleter = autocompleter

    function = autocompleter_registry.get(internal_autocompleter)

    if function is None:
        return problem(404, f"Autocompleter {autocompleter} not found.")

    try:
        choices = function(active_config, value, parameters)

    except KeyError as e:
        return problem(400, "Missing field", f"Missing field: {e}")

    result = {"choices": [{"id": k, "value": v} for k, v in choices if k is not None]}

    return serve_json(result)


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show, ignore_duplicates=ignore_duplicates)
