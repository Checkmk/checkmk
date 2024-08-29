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

from cmk.gui.http import Response
from cmk.gui.openapi.restful_objects import Endpoint
from cmk.gui.openapi.restful_objects.constructors import (
    collection_href,
    object_action_href,
    object_href,
)
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.quick_setup.to_frontend import (
    build_quick_setup_formspec_map,
    complete_quick_setup,
    quick_setup_overview,
    QuickSetupOverview,
    retrieve_next_stage,
    Stage,
    validate_stage,
)
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.definitions import IncomingStage, QuickSetupSaveRedirect

from cmk import fields

from .request_schemas import QuickSetupFinalSaveRequest, QuickSetupRequest
from .response_schemas import (
    QuickSetupOverviewResponse,
    QuickSetupSaveResponse,
    QuickSetupStageResponse,
)

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
    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        return _serve_error(
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )
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
    quick_setup_id = body["quick_setup_id"]
    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        return _serve_error(
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )
    stages_received = [IncomingStage(form_data=stage["form_data"]) for stage in body["stages"]]

    if (
        errors := validate_stage(
            quick_setup_id=quick_setup.id,
            stage=quick_setup.stages[len(stages_received) - 1],
            formspec_lookup=build_quick_setup_formspec_map(quick_setup.stages),
            stages_raw_formspecs=[stage.form_data for stage in stages_received],
        )
    ) is not None:
        return _serve_data(Stage(errors=errors), status_code=400)
    return _serve_data(
        data=retrieve_next_stage(quick_setup=quick_setup, incoming_stages=stages_received)
    )


@Endpoint(
    object_action_href("quick_setup", "{quick_setup_id}", "save"),
    "cmk/complete_quick_setup",
    method="post",
    tag_group="Checkmk Internal",
    path_params=[QUICKSETUP_ID],
    additional_status_codes=[201],
    request_schema=QuickSetupFinalSaveRequest,
    response_schema=QuickSetupSaveResponse,
)
def complete_quick_setup_action(params: Mapping[str, Any]) -> Response:
    """Save the quick setup"""
    body = params["body"]
    quick_setup_id = params["quick_setup_id"]
    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        return _serve_error(
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )
    incoming_stages = [IncomingStage(**stage) for stage in body["stages"]]
    return _serve_data(
        data=complete_quick_setup(quick_setup=quick_setup, incoming_stages=incoming_stages),
        status_code=201,
    )


def _serve_data(
    data: QuickSetupOverview | Stage | QuickSetupSaveRedirect,
    status_code: int = 200,
) -> Response:
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
    endpoint_registry.register(complete_quick_setup_action)
