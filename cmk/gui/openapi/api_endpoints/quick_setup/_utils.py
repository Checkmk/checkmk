#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import cast

from cmk.ccc.i18n import _
from cmk.gui.background_job.job import AlreadyRunningError
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.background_job import BACKGROUND_JOB_FAMILY
from cmk.gui.openapi.framework import ApiContext, RedirectException
from cmk.gui.openapi.framework.endpoint_link import path_to_endpoint
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.quick_setup.handlers.setup import (
    CompleteActionResult,
    QuickSetupAllStages,
    QuickSetupOverview,
    start_quick_setup_job,
    validate_stages_form_data,
    verify_custom_validators_and_complete_quick_setup,
)
from cmk.gui.quick_setup.handlers.stage import NextStageStructure, StageActionResult
from cmk.gui.quick_setup.handlers.utils import Action, Button, ButtonIcon, ValidationErrors
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.predefined import build_formspec_map_from_stages
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupActionMode, QuickSetupBackgroundAction
from cmk.gui.quick_setup.v0_unstable.type_defs import ActionId, RawFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.utils.roles import UserPermissionSerializableConfig

from .models.request_models import QuickSetupFinalActionRequestModel
from .models.response_models import (
    BackgroundJobExceptionModel,
    ButtonIconModel,
    ButtonModel,
    CompleteStageModel,
    QuickSetupCompleteResponseModel,
    QuickSetupGuidedResponseModel,
    QuickSetupOverviewResponseModel,
    QuickSetupStageActionResponseModel,
    StageActionModel,
    StageOverviewModel,
    StageStructureModel,
    ValidationErrorsModel,
)

QUICK_SETUP_PERMISSIONS = permissions.DynamicRuntimePerm(
    description="Required permissions depend on the quick setup configuration."
)


def _convert_button_icon(icon: ButtonIcon) -> ButtonIconModel:
    return ButtonIconModel(name=icon.name, rotate=icon.rotate)


def _convert_button(btn: Button) -> ButtonModel:
    return ButtonModel(
        label=btn.label,
        aria_label=btn.aria_label,
        icon=_convert_button_icon(btn.icon) if btn.icon else None,
    )


def _convert_action(action: Action) -> StageActionModel:
    return StageActionModel(
        id=action.id,
        button=_convert_button(action.button),
        load_wait_label=action.load_wait_label,
    )


def _convert_stage_structure(structure: NextStageStructure) -> StageStructureModel:
    return StageStructureModel(
        components=list(structure.components),
        actions=[_convert_action(a) for a in structure.actions],
        prev_button=_convert_button(structure.prev_button)
        if structure.prev_button is not None
        else None,
    )


def _convert_validation_errors(errors: ValidationErrors) -> ValidationErrorsModel:
    return ValidationErrorsModel(
        stage_index=errors.stage_index,
        formspec_errors=cast(dict[str, object], dict(errors.formspec_errors)),
        stage_errors=list(errors.stage_errors),
    )


def convert_guided_response(data: QuickSetupOverview) -> QuickSetupGuidedResponseModel:
    return QuickSetupGuidedResponseModel(
        mode="guided",
        quick_setup_id=data.quick_setup_id,
        actions=[_convert_action(a) for a in data.actions],
        prev_button=_convert_button(data.prev_button),
        guided_mode_string=data.guided_mode_string,
        overview_mode_string=data.overview_mode_string,
        overviews=[
            StageOverviewModel(title=o.title, sub_title=o.sub_title) for o in data.overviews
        ],
        stage=_convert_stage_structure(data.stage),
    )


def convert_overview_response(data: QuickSetupAllStages) -> QuickSetupOverviewResponseModel:
    return QuickSetupOverviewResponseModel(
        mode="overview",
        quick_setup_id=data.quick_setup_id,
        actions=[_convert_action(a) for a in data.actions],
        prev_button=None,
        guided_mode_string=data.guided_mode_string,
        overview_mode_string=data.overview_mode_string,
        stages=[
            CompleteStageModel(
                title=s.title,
                sub_title=s.sub_title,
                components=list(s.components),
                actions=[_convert_action(a) for a in s.actions],
                prev_button=_convert_button(s.prev_button),
            )
            for s in data.stages
        ],
    )


def convert_stage_action_response(result: StageActionResult) -> QuickSetupStageActionResponseModel:
    return QuickSetupStageActionResponseModel(
        stage_recap=list(result.stage_recap),
        validation_errors=(
            _convert_validation_errors(result.validation_errors)
            if result.validation_errors is not None
            else None
        ),
        background_job_exception=(
            BackgroundJobExceptionModel(
                message=result.background_job_exception.message,
                traceback=result.background_job_exception.traceback,
            )
            if result.background_job_exception is not None
            else None
        ),
    )


def convert_complete_response(result: CompleteActionResult) -> QuickSetupCompleteResponseModel:
    return QuickSetupCompleteResponseModel(
        redirect_url=result.redirect_url,
        all_stage_errors=(
            [_convert_validation_errors(e) for e in result.all_stage_errors]
            if result.all_stage_errors is not None
            else None
        ),
        background_job_exception=(
            BackgroundJobExceptionModel(
                message=result.background_job_exception.message,
                traceback=result.background_job_exception.traceback,
            )
            if result.background_job_exception is not None
            else None
        ),
    )


def complete_quick_setup_action(
    api_context: ApiContext,
    quick_setup_id: str,
    body: QuickSetupFinalActionRequestModel,
    mode: QuickSetupActionMode,
    object_id: str | None = None,
) -> ApiResponse[QuickSetupCompleteResponseModel]:
    """Shared logic for run and edit quick setup actions."""
    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        raise ProblemException(
            status=404,
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )

    action_id = body.button_id
    action = next((a for a in quick_setup.actions if a.id == action_id), None)
    if action is None:
        raise ProblemException(
            status=404,
            title="Action not found",
            detail=f"Action with id '{action_id}' does not exist.",
        )

    if action.permissions is not None and not all(user.may(perm) for perm in action.permissions):
        raise ProblemException(
            status=403,
            title="Action not allowed",
            detail=f"Action with id '{action_id}' requires {', '.join(repr(p) for p in action.permissions)} permissions.",
        )

    form_spec_map = build_formspec_map_from_stages([stage() for stage in quick_setup.stages])
    errors = validate_stages_form_data(
        stages_raw_form_data=[
            RawFormData(cast(Mapping[FormSpecId, object], stage.form_data)) for stage in body.stages
        ],
        quick_setup_formspec_map=form_spec_map,
    )

    if errors is not None:
        return ApiResponse(
            body=convert_complete_response(
                CompleteActionResult(
                    quick_setup_id=quick_setup.id,
                    action_id=ActionId(action_id),
                    all_stage_errors=list(add_summary_error_message(errors)),
                )
            ),
            status_code=400,
        )

    if isinstance(action, QuickSetupBackgroundAction):
        user_permission_config = UserPermissionSerializableConfig(
            roles=api_context.config.roles,
            user_roles={uid: u["roles"] for uid, u in api_context.config.multisite_users.items()},
            default_user_profile_roles=api_context.config.default_user_profile["roles"],
        )
        try:
            background_job_id = start_quick_setup_job(
                quick_setup=quick_setup,
                action_id=action.id,
                mode=mode,
                user_input_stages=[{"form_data": s.form_data} for s in body.stages],
                object_id=object_id,
                user_permission_config=user_permission_config,
                use_git=api_context.config.wato_use_git,
                pprint_value=api_context.config.wato_pprint_config,
            )
        except AlreadyRunningError:
            raise ProblemException(
                status=429,
                title="Cannot start action",
                detail="Another Quick setup action already running.",
            )
        location = path_to_endpoint(
            family=BACKGROUND_JOB_FAMILY.name,
            link_relation="cmk/show",
            version=api_context.version,
            parameters={"job_id": background_job_id},
        )
        raise RedirectException(location)

    result = verify_custom_validators_and_complete_quick_setup(
        quick_setup=quick_setup,
        action_id=ActionId(action_id),
        mode=mode,
        input_stages=[{"form_data": s.form_data} for s in body.stages],
        form_spec_map=form_spec_map,
        object_id=object_id,
        use_git=api_context.config.wato_use_git,
        pprint_value=api_context.config.wato_pprint_config,
    )

    if not result.redirect_url and not result.all_stage_errors:
        raise ValueError("The Quick setup action did not return a result")

    status_code = 201 if result.all_stage_errors is None else 400
    return ApiResponse(
        body=convert_complete_response(result),
        status_code=status_code,
    )


def add_summary_error_message(
    current_errors: Sequence[ValidationErrors],
) -> Sequence[ValidationErrors]:
    """Adds a summary error message if there is at least one error in a stage."""
    all_stage_errors: list[ValidationErrors] = list(current_errors)

    normalized_faulty_stage_numbers = sorted(
        err.stage_index + 1 for err in current_errors if err.stage_index is not None
    )

    msg = (
        _("Stages %s contain invalid form data. Please correct them and try again.")
        % ", ".join(str(index) for index in normalized_faulty_stage_numbers)
        if len(normalized_faulty_stage_numbers) > 1
        else _("Stage %s contains invalid form data. Please correct them and try again.")
        % normalized_faulty_stage_numbers[0]
    )

    all_stage_errors.append(
        ValidationErrors(
            stage_index=None,
            stage_errors=[msg],
        )
    )

    return all_stage_errors
