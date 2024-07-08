#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Quick setup

* GET quick setup overview
* POST validate stage and retrieve the next
"""

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from cmk.utils.encoding import json_encode
from cmk.utils.quick_setup.definitions import (
    IncomingStage,
    quick_setup_registry,
    QuickSetup,
    QuickSetupNotFoundException,
    QuickSetupOverview,
    Stage,
)

from cmk.gui.http import Response
from cmk.gui.openapi.restful_objects import Endpoint
from cmk.gui.openapi.restful_objects.constructors import collection_href, object_href
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.quick_setup.aws_stages import aws_quicksetup
from cmk.gui.quick_setup.to_frontend import quick_setup_overview, validate_current_stage

from cmk import fields

from .request_schemas import QuickSetupRequest
from .response_schemas import QuickSetupOverviewResponse, QuickSetupStageResponse

# TODO: CMK-18110: Investigate registration mechanism for Quick setups
quick_setup_registry.add_quick_setup(aws_quicksetup)


QUICKSETUP_ID = {
    "quick_setup_id": fields.String(
        required=True,
        description="The quick setup id",
        example="aws",
    )
}


@Endpoint(
    object_href("quick_setup", "{quick_setup_id}"),
    "cmk/quick_setup",
    method="get",
    tag_group="Checkmk Internal",
    path_params=[QUICKSETUP_ID],
    response_schema=QuickSetupOverviewResponse,
)
def get_all_stage_overviews_and_first_stage(params: Mapping[str, Any]) -> Response:
    """Get all stages overview together with the first stage components"""
    quick_setup_id = params["quick_setup_id"]
    try:
        quick_setup: QuickSetup = quick_setup_registry.get(quick_setup_id)
    except QuickSetupNotFoundException as exc:
        return _serve_error(title="Quick setup not found", detail=str(exc))
    return _serve_data(data=quick_setup_overview(quick_setup=quick_setup))


@Endpoint(
    collection_href("quick_setup"),
    "cmk/quick_setup",
    tag_group="Checkmk Internal",
    method="post",
    request_schema=QuickSetupRequest,
    response_schema=QuickSetupStageResponse,
)
def quicksetup_validate_stage_and_retrieve_next(params: Mapping[str, Any]) -> Response:
    """Validate the current stage and retrieve the next"""
    body = params["body"]
    quick_setup: QuickSetup = quick_setup_registry.get(body["quick_setup_id"])
    stages = [
        IncomingStage(stage_id=stage["stage_id"], form_data=stage["form_data"])
        for stage in body["stages"]
    ]

    next_stage = validate_current_stage(quick_setup=quick_setup, stages=stages)
    if next_stage.validation_errors:
        return _serve_data(data=next_stage, status_code=400)
    return _serve_data(data=next_stage)


def _serve_data(data: QuickSetupOverview | Stage, status_code: int = 200) -> Response:
    response = Response()
    response.set_content_type("application/json")
    response.set_data(json_encode(asdict(data)))
    response.status_code = status_code
    return response


def _serve_error(title: str, detail: str, status_code: int = 404) -> Response:
    response = Response()
    response.set_content_type("application/problem+json")
    response.set_data(json_encode({"title": title, "detail": detail}))
    response.status_code = status_code
    return response


def register(endpoint_registry: EndpointRegistry) -> None:
    endpoint_registry.register(get_all_stage_overviews_and_first_stage)
    endpoint_registry.register(quicksetup_validate_stage_and_retrieve_next)
