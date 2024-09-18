#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Quick setup

* GET quick setup guided stages or overview stages
* POST validate stage and retrieve the next
* POST complete the quick setup and save
"""

from collections.abc import Mapping
from dataclasses import asdict
from enum import StrEnum
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
    complete_quick_setup,
    quick_setup_guided_mode,
    quick_setup_overview_mode,
    QuickSetupAllStages,
    QuickSetupOverview,
    retrieve_next_stage,
    Stage,
    validate_stage,
)
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.definitions import QuickSetupSaveRedirect
from cmk.gui.quick_setup.v0_unstable.type_defs import RawFormData

from cmk import fields

from .request_schemas import QuickSetupFinalSaveRequest, QuickSetupRequest
from .response_schemas import (
    QuickSetupResponse,
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


class QuickSetupMode(StrEnum):
    GUIDED = "guided"
    OVERVIEW = "overview"


QUICKSETUP_MODE = {
    "mode": fields.String(
        enum=[mode.value for mode in QuickSetupMode],
        required=False,
        description="The quick setup mode",
        example="overview",
        load_default="guided",
    )
}


@Endpoint(
    object_href("quick_setup", "{quick_setup_id}"),
    "cmk/quick_setup",
    method="get",
    tag_group="Checkmk Internal",
    query_params=[QUICKSETUP_MODE],
    path_params=[QUICKSETUP_ID],
    response_schema=QuickSetupResponse,
)
def get_guided_stages_or_overview_stages(params: Mapping[str, Any]) -> Response:
    """Get guided stages or overview stages"""
    quick_setup_id = params["quick_setup_id"]
    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        return _serve_error(
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )

    mode: QuickSetupMode = params["mode"]
    match mode:
        case QuickSetupMode.OVERVIEW.value:
            return _serve_data(data=quick_setup_overview_mode(quick_setup=quick_setup))
        case QuickSetupMode.GUIDED.value:
            return _serve_data(data=quick_setup_guided_mode(quick_setup=quick_setup))
        case _:
            return _serve_error(
                title="Invalid mode",
                detail=f"The mode {mode} is not one of {[mode.value for mode in QuickSetupMode]}",
                status_code=400,
            )


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
    if (quick_setup := quick_setup_registry.get(quick_setup_id)) is None:
        return _serve_error(
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )

    if (
        errors := validate_stage(
            quick_setup=quick_setup,
            stages_raw_formspecs=[RawFormData(stage["form_data"]) for stage in body["stages"]],
        )
    ) is not None:
        return _serve_data(Stage(errors=errors), status_code=400)
    return _serve_data(
        data=retrieve_next_stage(
            quick_setup=quick_setup,
            stages_raw_formspecs=[RawFormData(stage["form_data"]) for stage in body["stages"]],
        )
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
    return _serve_data(
        data=complete_quick_setup(
            quick_setup=quick_setup,
            stages_raw_formspecs=[RawFormData(stage["form_data"]) for stage in body["stages"]],
        ),
        status_code=201,
    )


def _serve_data(
    data: QuickSetupOverview | Stage | QuickSetupSaveRedirect | QuickSetupAllStages,
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
    endpoint_registry.register(get_guided_stages_or_overview_stages)
    endpoint_registry.register(quicksetup_validate_stage_and_retrieve_next)
    endpoint_registry.register(complete_quick_setup_action)
