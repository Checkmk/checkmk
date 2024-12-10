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
from urllib.parse import urlparse

from pydantic import BaseModel

from cmk.utils.encoding import json_encode

from cmk.gui.http import Response
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.constructors import (
    collection_href,
    object_action_href,
    object_href,
)
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.quick_setup.to_frontend import (
    AllStageErrors,
    complete_quick_setup,
    get_stages_and_formspec_map,
    matching_stage_action,
    quick_setup_guided_mode,
    quick_setup_overview_mode,
    QuickSetupAllStages,
    QuickSetupOverview,
    StageActionResult,
    start_quick_setup_stage_job,
    validate_custom_validators,
    validate_stage_and_retrieve_next_stage_structure,
    validate_stages_formspecs,
    ValidationAndNextStage,
)
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.definitions import QuickSetupSaveRedirect
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupActionMode
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData, RawFormData, StageIndex

from cmk import fields

from .. import background_job
from .request_schemas import QuickSetupFinalSaveRequest, QuickSetupRequest
from .response_schemas import (
    QuickSetupCompleteResponse,
    QuickSetupResponse,
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

QUICKSETUP_OBJECT_ID = {
    "object_id": fields.String(
        required=False,
        description="Select object id to prefill data for the quick setup",
        example="8558f956-3e45-4c4f-bd02-e88da17c99dd",
        load_default="",
    )
}

QUICKSETUP_OBJECT_ID_REQUIRED = {
    "object_id": fields.String(
        required=True,
        description="Select object id to prefill data for the quick setup",
        example="8558f956-3e45-4c4f-bd02-e88da17c99dd",
    )
}

JOB_ID = {
    "job_id": fields.String(
        required=True,
        description="The id of the action job result to be fetched",
        example="quick_setup",
    )
}


@Endpoint(
    object_href("quick_setup", "{quick_setup_id}"),
    "cmk/quick_setup",
    method="get",
    tag_group="Checkmk Internal",
    query_params=[QUICKSETUP_MODE, QUICKSETUP_OBJECT_ID],
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
    prefill_data: ParsedFormData | None = None
    if object_id := params["object_id"]:
        prefill_data = quick_setup.load_data(object_id)
        if not prefill_data:
            return _serve_error(
                title="Object not found",
                detail=f"Object with id '{object_id}' does not exist.",
            )
    match mode:
        case QuickSetupMode.OVERVIEW.value:
            return _serve_data(
                data=quick_setup_overview_mode(quick_setup=quick_setup, prefill_data=prefill_data)
            )
        case QuickSetupMode.GUIDED.value:
            return _serve_data(
                data=quick_setup_guided_mode(quick_setup=quick_setup, prefill_data=prefill_data)
            )
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
    status_descriptions={
        303: "The stage validation and retrieval action has been started in the background. "
        "Redirecting to the 'Get background job status snapshot' endpoint."
    },
    additional_status_codes=[303],
    query_params=[QUICKSETUP_OBJECT_ID],
    request_schema=QuickSetupRequest,
    response_schema=QuickSetupStageResponse,
)
def quicksetup_validate_stage_and_retrieve_next(params: Mapping[str, Any]) -> Response:
    """Validate the current stage and retrieve the next"""
    body = params["body"]
    quick_setup_id = body["quick_setup_id"]
    stage_action_id = body["stage_action_id"]

    if (quick_setup := quick_setup_registry.get(quick_setup_id)) is None:
        return _serve_error(
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )

    stage_index = StageIndex(len(body["stages"]) - 1)
    stage_action = matching_stage_action(quick_setup.stages[stage_index](), stage_action_id)
    if stage_action.run_in_background:
        background_job_id = start_quick_setup_stage_job(
            quick_setup=quick_setup,
            action_id=stage_action_id,
            stage_index=stage_index,
            user_input_stages=body["stages"],
            object_id=params["object_id"],
        )
        background_job_status_link = constructors.link_endpoint(
            module_name="cmk.gui.openapi.endpoints.background_job",
            rel="cmk/show",
            parameters={background_job.JobID.field_name: background_job_id},
        )
        response = Response(status=303)
        response.location = urlparse(background_job_status_link["href"]).path
        return response

    result = validate_stage_and_retrieve_next_stage_structure(
        quick_setup=quick_setup,
        stage_index=stage_index,
        stage_action_id=stage_action_id,
        input_stages=body["stages"],
        object_id=params["object_id"],
    )
    return _serve_data(result, status_code=200 if result.errors is None else 400)


@Endpoint(
    object_href("quick_setup_stage_action_result", "{job_id}"),
    "cmk/fetch",
    tag_group="Checkmk Internal",
    method="get",
    path_params=[JOB_ID],
    response_schema=QuickSetupStageResponse,
)
def fetch_quick_setup_stage_action_result(params: Mapping[str, Any]) -> Response:
    """Fetch the Quick setup stage action background job result"""
    action_background_job_id = params["job_id"]
    action_result = StageActionResult.load_from_job_result(job_id=action_background_job_id)
    return _serve_action_result(action_result)


@Endpoint(
    object_action_href("quick_setup", "{quick_setup_id}", "save"),
    "cmk/save_quick_setup",
    method="post",
    tag_group="Checkmk Internal",
    path_params=[QUICKSETUP_ID],
    query_params=[QUICKSETUP_MODE],
    additional_status_codes=[201],
    request_schema=QuickSetupFinalSaveRequest,
    response_schema=QuickSetupCompleteResponse,
)
def save_quick_setup_action(params: Mapping[str, Any]) -> Response:
    """Save the quick setup"""
    return complete_quick_setup_action(params, QuickSetupActionMode.SAVE)


@Endpoint(
    object_action_href("quick_setup", "{quick_setup_id}", "edit"),
    "cmk/edit_quick_setup",
    method="put",
    tag_group="Checkmk Internal",
    path_params=[QUICKSETUP_ID],
    query_params=[QUICKSETUP_OBJECT_ID_REQUIRED],
    additional_status_codes=[201],
    request_schema=QuickSetupFinalSaveRequest,
    response_schema=QuickSetupCompleteResponse,
)
def edit_quick_setup_action(params: Mapping[str, Any]) -> Response:
    """Edit the quick setup"""
    return complete_quick_setup_action(params, QuickSetupActionMode.EDIT)


def complete_quick_setup_action(params: Mapping[str, Any], mode: QuickSetupActionMode) -> Response:
    """Complete the quick setup action

    This function handles the overall Quick setup action. This is usually at the very end of the
    Quick setup flow. Multiple actions are performed here before the actual complete action:

    1. Validate formspecs (of all stages)
        - We validate again (in 'guided' mode) as there is a formspec validation when progressing
        from one stage to the next
        - the custom validators of the individual stages are not validated again
    2. Run Quick setup validators
    3. Perform Quick setup complete action
    """
    body = params["body"]
    quick_setup_id = params["quick_setup_id"]
    action_id = body["button_id"]
    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        return _serve_error(
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )

    stage_index = StageIndex(len(body["stages"]) - 1)
    _stages, form_spec_map = get_stages_and_formspec_map(
        quick_setup=quick_setup,
        stage_index=stage_index,
    )

    stages_raw_formspecs = [RawFormData(stage["form_data"]) for stage in body["stages"]]
    if (
        stage_errors := validate_stages_formspecs(
            stages_raw_formspecs=stages_raw_formspecs,
            quick_setup_formspec_map=form_spec_map,
        )
    ) is not None:
        return _serve_data(
            AllStageErrors(
                all_stage_errors=stage_errors,
            ),
            status_code=400,
        )

    action = next((action for action in quick_setup.actions if action.id == action_id), None)
    if action is None:
        return _serve_error(
            title="Save action not found",
            detail=f"Save action with id '{action_id}' does not exist.",
        )

    errors = validate_custom_validators(
        quick_setup_id=quick_setup_id,
        custom_validators=action.custom_validators,
        stages_raw_formspecs=stages_raw_formspecs,
        quick_setup_formspec_map=form_spec_map,
    )
    if errors.exist():
        return _serve_data(
            AllStageErrors(
                all_stage_errors=[errors],
            ),
            status_code=400,
        )

    return _serve_data(
        complete_quick_setup(
            action=action,
            mode=mode,
            stages_raw_formspecs=stages_raw_formspecs,
            quick_setup_formspec_map=form_spec_map,
            object_id=params.get("object_id"),
        ),
        status_code=201,
    )


def _serve_data(
    data: QuickSetupOverview
    | QuickSetupSaveRedirect
    | QuickSetupAllStages
    | AllStageErrors
    | ValidationAndNextStage,
    status_code: int = 200,
) -> Response:
    return _prepare_response(asdict(data), status_code)


def _serve_action_result(data: BaseModel, status_code: int = 200) -> Response:
    return _prepare_response(data.model_dump(), status_code)


def _prepare_response(data: dict, status_code: int) -> Response:
    response = Response()
    response.set_content_type("application/json")
    response.set_data(json_encode(data))
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
    endpoint_registry.register(fetch_quick_setup_stage_action_result)
    endpoint_registry.register(save_quick_setup_action)
    endpoint_registry.register(edit_quick_setup_action)
