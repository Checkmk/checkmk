#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Quick setup

* GET quick setup guided stages or overview stages
* GET a quick setup stage structure
* POST validate stage
* POST complete the quick setup and save
"""

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel

from cmk.ccc.i18n import _

from cmk.utils.encoding import json_encode

from cmk.gui.http import Response
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.constructors import (
    object_action_href,
    object_href,
    sub_object_href,
)
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.quick_setup.handlers.setup import (
    CompleteActionResult,
    quick_setup_guided_mode,
    quick_setup_overview_mode,
    QuickSetupAllStages,
    QuickSetupOverview,
    start_quick_setup_job,
    validate_stages_form_data,
    verify_custom_validators_and_complete_quick_setup,
)
from cmk.gui.quick_setup.handlers.stage import (
    get_stage_structure,
    matching_stage_action,
    NextStageStructure,
    StageActionResult,
    start_quick_setup_stage_job,
    validate_stage_formspecs,
    verify_custom_validators_and_recap_stage,
)
from cmk.gui.quick_setup.handlers.utils import ValidationErrors
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.definitions import QuickSetupSaveRedirect
from cmk.gui.quick_setup.v0_unstable.predefined import build_formspec_map_from_stages
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupActionMode
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData, RawFormData, StageIndex

from cmk import fields

from .. import background_job
from .request_schemas import (
    QuickSetupFinalActionRequest,
    QuickSetupStageActionRequest,
)
from .response_schemas import (
    QuickSetupCompleteResponse,
    QuickSetupResponse,
    QuickSetupStageActionResponse,
    QuickSetupStageStructure,
)

QUICKSETUP_ID = {
    "quick_setup_id": fields.String(
        required=True,
        description="The quick setup id",
        example="aws",
    )
}

STAGE_INDEX = {
    "stage_index": fields.String(
        required=True,
        description="The stage index",
        example="1",
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
    sub_object_href(
        domain_type="quick_setup_stage",
        parent_domain_type="quick_setup",
        obj_id="{stage_index}",
        parent_id="{quick_setup_id}",
    ),
    "cmk/fetch",
    tag_group="Checkmk Internal",
    method="get",
    path_params=[QUICKSETUP_ID, STAGE_INDEX],
    query_params=[QUICKSETUP_OBJECT_ID],
    response_schema=QuickSetupStageStructure,
)
def quick_setup_get_stage_structure(params: Mapping[str, Any]) -> Response:
    """Get a Quick setup stage structure"""
    quick_setup_id = params["quick_setup_id"]
    object_id = params.get("object_id")
    stage_index = int(params["stage_index"])
    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        return _serve_error(
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )

    prefill_data: ParsedFormData | None = None
    if object_id:
        prefill_data = quick_setup.load_data(object_id)
        if not prefill_data:
            return _serve_error(
                title="Object not found",
                detail=f"Object with id '{object_id}' does not exist.",
            )

    return _serve_data(
        get_stage_structure(
            stage=quick_setup.stages[stage_index](),
            prefill_data=prefill_data,
        )
    )


@Endpoint(
    object_action_href("quick_setup", "{quick_setup_id}", "run-stage-action"),
    "cmk/run",
    tag_group="Checkmk Internal",
    method="post",
    status_descriptions={
        303: "The stage validation and recap action has been started in the background. "
        "Redirecting to the 'Get background job status snapshot' endpoint."
    },
    additional_status_codes=[303],
    path_params=[QUICKSETUP_ID],
    request_schema=QuickSetupStageActionRequest,
    response_schema=QuickSetupStageActionResponse,
)
def quicksetup_run_stage_action(params: Mapping[str, Any]) -> Response:
    """Run a Quick setup stage validation and recap action"""
    body = params["body"]
    quick_setup_id = params["quick_setup_id"]
    stage_action_id = body["stage_action_id"]

    if (quick_setup := quick_setup_registry.get(quick_setup_id)) is None:
        return _serve_error(
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )

    stage_index = StageIndex(len(body["stages"]) - 1)
    stage_action = matching_stage_action(quick_setup.stages[stage_index](), stage_action_id)

    built_stages = [stage() for stage in quick_setup.stages[: stage_index + 1]]
    form_spec_map = build_formspec_map_from_stages(built_stages)
    # Validate the stage formspec data; this is separate from the custom validators of the stage
    # as the custom validators can potentially take a long time (and therefore be run in a
    # background job)
    errors = validate_stage_formspecs(
        stage_index=stage_index,
        stages_raw_formspecs=[RawFormData(stage["form_data"]) for stage in body["stages"]],
        quick_setup_formspec_map=form_spec_map,
    )
    if errors.exist():
        return _serve_action_result(
            StageActionResult(validation_errors=errors),
            status_code=400,
        )

    if stage_action.run_in_background:
        background_job_id = start_quick_setup_stage_job(
            quick_setup=quick_setup,
            action_id=stage_action_id,
            stage_index=stage_index,
            user_input_stages=body["stages"],
        )
        background_job_status_link = constructors.link_endpoint(
            module_name="cmk.gui.openapi.endpoints.background_job",
            rel="cmk/show",
            parameters={background_job.JobID.field_name: background_job_id},
        )
        response = Response(status=303)
        response.location = urlparse(background_job_status_link["href"]).path
        return response

    result = verify_custom_validators_and_recap_stage(
        quick_setup=quick_setup,
        stage_index=stage_index,
        stage_action_id=stage_action_id,
        input_stages=body["stages"],
        form_spec_map=form_spec_map,
        built_stages=built_stages,
    )
    return _serve_action_result(
        result, status_code=200 if result.validation_errors is None else 400
    )


@Endpoint(
    object_href("quick_setup_stage_action_result", "{job_id}"),
    "cmk/fetch",
    tag_group="Checkmk Internal",
    method="get",
    path_params=[JOB_ID],
    response_schema=QuickSetupStageActionResponse,
)
def fetch_quick_setup_stage_action_result(params: Mapping[str, Any]) -> Response:
    """Fetch the Quick setup stage action background job result"""
    action_background_job_id = params["job_id"]
    action_result = StageActionResult.load_from_job_result(job_id=action_background_job_id)
    return _serve_action_result(action_result)


@Endpoint(
    object_action_href("quick_setup", "{quick_setup_id}", "run-action"),
    "cmk/run_setup",
    method="post",
    tag_group="Checkmk Internal",
    path_params=[QUICKSETUP_ID],
    query_params=[QUICKSETUP_MODE],
    additional_status_codes=[201, 303],
    status_descriptions={
        303: "The validation and complete action has been started in the background. "
        "Redirecting to the 'Get background job status snapshot' endpoint."
    },
    request_schema=QuickSetupFinalActionRequest,
    response_schema=QuickSetupCompleteResponse,
)
def quick_setup_run_action(params: Mapping[str, Any]) -> Response:
    """Run a quick setup action"""
    return complete_quick_setup_action(params, QuickSetupActionMode.SAVE)


@Endpoint(
    object_action_href("quick_setup", "{quick_setup_id}", "edit"),
    "cmk/edit_quick_setup",
    method="put",
    tag_group="Checkmk Internal",
    path_params=[QUICKSETUP_ID],
    query_params=[QUICKSETUP_OBJECT_ID_REQUIRED],
    additional_status_codes=[201, 303],
    status_descriptions={
        303: "The validation and complete action has been started in the background. "
        "Redirecting to the 'Get background job status snapshot' endpoint."
    },
    request_schema=QuickSetupFinalActionRequest,
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
    object_id = params.get("object_id")
    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        return _serve_error(
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )

    action = next((action for action in quick_setup.actions if action.id == action_id), None)
    if action is None:
        return _serve_error(
            title="Action not found",
            detail=f"Action with id '{action_id}' does not exist.",
        )

    form_spec_map = build_formspec_map_from_stages([stage() for stage in quick_setup.stages])
    errors = validate_stages_form_data(
        stages_raw_form_data=[RawFormData(stage["form_data"]) for stage in body["stages"]],
        quick_setup_formspec_map=form_spec_map,
    )

    if errors is not None:
        return _serve_action_result(
            CompleteActionResult(all_stage_errors=_add_summary_error_message(errors)),
            status_code=400,
        )

    if action.run_in_background:
        background_job_id = start_quick_setup_job(
            quick_setup=quick_setup,
            action_id=action.id,
            mode=mode,
            user_input_stages=body["stages"],
            object_id=object_id,
        )
        background_job_status_link = constructors.link_endpoint(
            module_name="cmk.gui.openapi.endpoints.background_job",
            rel="cmk/show",
            parameters={background_job.JobID.field_name: background_job_id},
        )
        response = Response(status=303)
        response.location = urlparse(background_job_status_link["href"]).path
        return response

    result = verify_custom_validators_and_complete_quick_setup(
        quick_setup=quick_setup,
        action_id=action_id,
        mode=mode,
        input_stages=body["stages"],
        form_spec_map=form_spec_map,
        object_id=object_id,
    )

    if not result.redirect_url and not result.all_stage_errors:
        raise ValueError("The Quick setup action did not return a result")

    return _serve_action_result(result, status_code=201 if result.all_stage_errors is None else 400)


@Endpoint(
    object_href("quick_setup_action_result", "{job_id}"),
    ".../fetch",
    tag_group="Checkmk Internal",
    method="get",
    path_params=[JOB_ID],
    response_schema=QuickSetupCompleteResponse,
)
def fetch_quick_setup_action_result(params: Mapping[str, Any]) -> Response:
    """Fetch the Quick action background job result"""
    action_background_job_id = params["job_id"]
    action_result = CompleteActionResult.load_from_job_result(job_id=action_background_job_id)
    return _serve_action_result(action_result)


def _serve_data(
    data: QuickSetupOverview | QuickSetupSaveRedirect | QuickSetupAllStages | NextStageStructure,
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


def _add_summary_error_message(
    current_errors: Sequence[ValidationErrors],
) -> Sequence[ValidationErrors]:
    """
    This method will add a summary error message if there is at least one error in a stage
    """

    all_stage_errors: list[ValidationErrors] = []
    all_stage_errors.extend(current_errors)

    faulty_stage_indices = [
        err.stage_index for err in current_errors if err.stage_index is not None
    ]
    faulty_stage_indices.sort()

    msg = (
        _("Stages %s contain invalid form data. Please correct them and try again.")
        % ", ".join(str(index + 1) for index in faulty_stage_indices)
        if len(faulty_stage_indices) > 1
        else _("Stage %s contains invalid form data. Please correct them and try again.")
        % faulty_stage_indices[0]
    )

    all_stage_errors.append(
        ValidationErrors(
            stage_index=None,
            stage_errors=[msg],
        )
    )

    return all_stage_errors


def _serve_error(title: str, detail: str, status_code: int = 404) -> Response:
    response = Response()
    response.set_content_type("application/problem+json")
    response.set_data(json_encode({"title": title, "detail": detail}))
    response.status_code = status_code
    return response


def register(endpoint_registry: EndpointRegistry) -> None:
    endpoint_registry.register(get_guided_stages_or_overview_stages)
    endpoint_registry.register(quick_setup_get_stage_structure)
    endpoint_registry.register(quicksetup_run_stage_action)
    endpoint_registry.register(fetch_quick_setup_stage_action_result)
    endpoint_registry.register(quick_setup_run_action)
    endpoint_registry.register(edit_quick_setup_action)
    endpoint_registry.register(fetch_quick_setup_action_result)
