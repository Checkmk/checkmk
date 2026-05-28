#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Any, Literal

from pydantic import Discriminator

from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class ButtonIconModel:
    name: str = api_field(description="Name of the icon.", example="next")
    rotate: int = api_field(description="Rotation in degrees for the icon", example=90)


@api_model
class ButtonModel:
    label: str = api_field(description="The label of the button", example="Next")
    aria_label: str | None = api_field(description="The aria label of the button", example="Next")
    icon: ButtonIconModel | None = api_field(
        description="Definition of the button icon",
        example={"name": "save-to-service", "rotate": 0},
    )


@api_model
class StageActionModel:
    id: str = api_field(description="The action id", example="action")
    button: ButtonModel = api_field(
        description="Definition of the action button",
        example={"label": "Next", "aria_label": "Next"},
    )
    load_wait_label: str = api_field(
        description="A string to display while waiting for the next stage",
        example="Please wait...",
    )


@api_model
class StageOverviewModel:
    title: str = api_field(description="The title of a stage", example="Prepare AWS for Checkmk")
    sub_title: str | None = api_field(description="The sub-title of a stage", example="aws")


@api_model
class StageStructureModel:
    components: list[dict[str, Any]] = api_field(
        description="A collection of stage components", example=[]
    )
    actions: list[StageActionModel] = api_field(
        description="A collection of stage actions", example=[]
    )
    prev_button: ButtonModel | None = api_field(
        description="Definition of the `go to previous stage` button",
        example={"label": "Back"},
    )


@api_model
class ValidationErrorsModel:
    stage_index: int | None = api_field(
        description="Index of the stage containing errors.", example=0
    )
    formspec_errors: dict[str, Any] = api_field(
        description="A mapping of formspec ids to formspec validation errors",
        example={},
    )
    stage_errors: list[str] = api_field(
        description="A collection of general stage errors", example=[]
    )


@api_model
class BackgroundJobExceptionModel:
    message: str = api_field(description="The exception message", example="An exception message")
    traceback: str = api_field(
        description="The traceback of the exception",
        example="The traceback of the background job exception",
    )


@api_model
class QuickSetupStageActionResponseModel:
    stage_recap: list[dict[str, Any]] = api_field(
        description="A collection of widget recaps", example=[]
    )
    validation_errors: ValidationErrorsModel | None = api_field(
        description="All formspec errors and general stage errors", example={}
    )
    background_job_exception: BackgroundJobExceptionModel | None = api_field(
        description=(
            "The exception details if the action was run in the background and raised an "
            "unexpected exception"
        ),
        example={},
    )


@api_model
class CompleteStageModel:
    title: str = api_field(description="The title of a stage", example="Prepare AWS for Checkmk")
    sub_title: str | None = api_field(description="The sub-title of a stage", example="aws")
    components: list[dict[str, Any]] = api_field(
        description="A collection of stage components", example=[]
    )
    actions: list[StageActionModel] = api_field(
        description="A collection of stage actions", example=[]
    )
    prev_button: ButtonModel | None = api_field(
        description="Definition of the `go to previous stage` button",
        example={"label": "Back"},
    )


@api_model
class QuickSetupGuidedResponseModel:
    mode: Literal["guided"] = api_field(description="The quick setup mode", example="guided")
    quick_setup_id: str = api_field(description="The quicksetup id", example="aws_quicksetup")
    actions: list[StageActionModel] = api_field(
        description="A list of all complete actions",
        example=[{"id": "save", "label": "Save configuration"}],
    )
    prev_button: ButtonModel | None = api_field(
        description="Definition of the `go to previous stage` button",
        example={"label": "Back", "aria_label": "Back"},
    )
    guided_mode_string: str = api_field(
        description="The string for the guided mode label", example="Guided mode"
    )
    overview_mode_string: str = api_field(
        description="The string for the overview mode label", example="Overview mode"
    )
    overviews: list[StageOverviewModel] = api_field(
        description="The overview of the quicksetup stages",
        example=[],
    )
    stage: StageStructureModel = api_field(
        description="The first stage",
        example={"components": []},
    )


@api_model
class QuickSetupOverviewResponseModel:
    mode: Literal["overview"] = api_field(description="The quick setup mode", example="overview")
    quick_setup_id: str = api_field(description="The quicksetup id", example="aws_quicksetup")
    actions: list[StageActionModel] = api_field(
        description="A list of all complete actions",
        example=[{"id": "save", "label": "Save configuration"}],
    )
    prev_button: ButtonModel | None = api_field(
        description="Definition of the `go to previous stage` button",
        example={"label": "Back", "aria_label": "Back"},
    )
    guided_mode_string: str = api_field(
        description="The string for the guided mode label", example="Guided mode"
    )
    overview_mode_string: str = api_field(
        description="The string for the overview mode label", example="Overview mode"
    )
    stages: list[CompleteStageModel] = api_field(
        description="A list of all stages and their components",
        example=[],
    )


type QuickSetupResponseModel = Annotated[
    QuickSetupGuidedResponseModel | QuickSetupOverviewResponseModel, Discriminator("mode")
]


@api_model
class QuickSetupCompleteResponseModel:
    redirect_url: str | None = api_field(
        description="The url to redirect to after saving the quicksetup",
        example="http://save/url",
    )
    all_stage_errors: list[ValidationErrorsModel] | None = api_field(
        description="A list of stage errors", example=[]
    )
    background_job_exception: BackgroundJobExceptionModel | None = api_field(
        description=(
            "The exception details if the action was run in the background and raised an "
            "unexpected exception"
        ),
        example={},
    )
