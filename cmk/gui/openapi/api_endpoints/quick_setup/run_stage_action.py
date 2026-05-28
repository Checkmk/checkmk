#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Annotated, cast

from cmk.ccc.site import SiteId
from cmk.gui import i18n
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.background_job import BACKGROUND_JOB_FAMILY
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    RedirectException,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.endpoint_link import path_to_endpoint
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.quick_setup.handlers.stage import (
    matching_stage_action,
    start_quick_setup_stage_action_job_on_remote,
    start_quick_setup_stage_job,
    validate_stage_formspecs,
    verify_custom_validators_and_recap_stage,
)
from cmk.gui.quick_setup.handlers.utils import form_spec_parse
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.predefined import build_formspec_map_from_stages
from cmk.gui.quick_setup.v0_unstable.predefined._common import find_id_in_form_data
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupBackgroundStageAction
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ActionId,
    QuickSetupId,
    RawFormData,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.site_config import site_is_local
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.watolib.automations import (
    remote_automation_config_from_site_config,
)

from ._family import QUICK_SETUP_FAMILY
from ._utils import (
    _convert_validation_errors,
    convert_stage_action_response,
    QUICK_SETUP_PERMISSIONS,
)
from .models.request_models import QuickSetupStageActionRequestModel
from .models.response_models import QuickSetupStageActionResponseModel


def run_stage_action_v1(
    api_context: ApiContext,
    quick_setup_id: Annotated[str, PathParam(description="The quick setup id", example="aws")],
    body: QuickSetupStageActionRequestModel,
) -> ApiResponse[QuickSetupStageActionResponseModel]:
    """Run a Quick setup stage validation and recap action

    This endpoint performs permission validation but since permissions depend on dynamic actions
    and each action has its own required permission, they cannot be statically defined. If the
    required permissions for an action are not met, the endpoint returns a 403 Forbidden error
    informing the action ID and the missing permission.
    """
    language = user.language
    stage_action_id = body.stage_action_id

    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        raise ProblemException(
            status=404,
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )

    stage_index = StageIndex(len(body.stages) - 1)
    stage_action = matching_stage_action(
        quick_setup.stages[stage_index](), ActionId(stage_action_id)
    )

    if stage_action.permissions is not None and not all(
        user.may(perm) for perm in stage_action.permissions
    ):
        raise ProblemException(
            status=403,
            title="Action not allowed",
            detail=(
                f"Action with id '{stage_action_id}' requires "
                f"{', '.join(repr(x) for x in stage_action.permissions)} permissions."
            ),
        )

    built_stages = [stage() for stage in quick_setup.stages[: stage_index + 1]]
    form_spec_map = build_formspec_map_from_stages(built_stages)
    stages_raw_formspecs = [
        RawFormData(cast(Mapping[FormSpecId, object], stage.form_data)) for stage in body.stages
    ]
    errors = validate_stage_formspecs(
        stage_index=stage_index,
        stages_raw_formspecs=stages_raw_formspecs,
        quick_setup_formspec_map=form_spec_map,
    )
    if errors.exist():
        return ApiResponse(
            body=QuickSetupStageActionResponseModel(
                stage_recap=[],
                validation_errors=_convert_validation_errors(errors),
                background_job_exception=None,
            ),
            status_code=400,
        )

    user_permission_config = UserPermissionSerializableConfig(
        roles=api_context.config.roles,
        user_roles={uid: u["roles"] for uid, u in api_context.config.multisite_users.items()},
        default_user_profile_roles=api_context.config.default_user_profile["roles"],
    )

    if isinstance(stage_action, QuickSetupBackgroundStageAction):
        site_id = None
        if stage_action.target_site_formspec_key:
            site_id = find_id_in_form_data(
                form_spec_parse(stages_raw_formspecs, form_spec_map),
                target_key=stage_action.target_site_formspec_key,
            )
            assert site_id is not None

        if site_id and not site_is_local(api_context.config.sites[SiteId(site_id)]):
            background_job_id = start_quick_setup_stage_action_job_on_remote(
                site_id=SiteId(site_id),
                automation_config=remote_automation_config_from_site_config(
                    api_context.config.sites[SiteId(site_id)]
                ),
                user_permission_config=user_permission_config,
                quick_setup_id=QuickSetupId(quick_setup_id),
                action_id=ActionId(stage_action_id),
                stage_index=stage_index,
                user_input_stages=[{"form_data": s.form_data} for s in body.stages],
                language=language,
                debug=api_context.config.debug,
            )
        else:
            background_job_id = start_quick_setup_stage_job(
                quick_setup_id=quick_setup.id,
                action_id=ActionId(stage_action_id),
                stage_index=stage_index,
                user_input_stages=[{"form_data": s.form_data} for s in body.stages],
                language=language,
                user_permission_config=user_permission_config,
                job_uuid=None,
            )

        parameters: dict[str, str] = {"job_id": background_job_id}
        if site_id and not site_is_local(api_context.config.sites[SiteId(site_id)]):
            parameters["site_id"] = site_id
        location = path_to_endpoint(
            family=BACKGROUND_JOB_FAMILY.name,
            link_relation="cmk/show",
            version=api_context.version,
            parameters=parameters,
        )
        raise RedirectException(location)

    i18n.localize(language)
    result = verify_custom_validators_and_recap_stage(
        quick_setup=quick_setup,
        stage_index=stage_index,
        stage_action_id=ActionId(stage_action_id),
        input_stages=[{"form_data": s.form_data} for s in body.stages],
        form_spec_map=form_spec_map,
        built_stages=built_stages,
        progress_logger=None,
        site_configs=api_context.config.sites,
        debug=api_context.config.debug,
    )
    status_code = 200 if result.validation_errors is None else 400
    return ApiResponse(
        body=convert_stage_action_response(result),
        status_code=status_code,
    )


ENDPOINT_RUN_STAGE_ACTION = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("quick_setup", "{quick_setup_id}", "run-stage-action"),
        link_relation="cmk/run",
        method="post",
    ),
    permissions=EndpointPermissions(required=QUICK_SETUP_PERMISSIONS),
    doc=EndpointDoc(
        family=QUICK_SETUP_FAMILY.name,
    ),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=run_stage_action_v1,
            additional_status_codes=[303, 403],
        )
    },
)
