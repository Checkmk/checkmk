#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow_oneofschema import OneOfSchema

from cmk.gui.fields.utils import BaseSchema

from cmk import fields


class QuickSetupStageOverviewResponse(BaseSchema):
    title = fields.String(
        example="Prepare AWS for Checkmk",
        description="The title of a stage",
    )
    sub_title = fields.String(
        example="aws",
        description="The sub-title of a stage",
        allow_none=True,
    )


class Errors(BaseSchema):
    stage_index = fields.Integer(
        example=0,
        description="Index of the stage containing errors.",
        allow_none=True,
    )
    formspec_errors = fields.Dict(
        example={},
        description="A mapping of formspec ids to formspec validation errors",
    )
    stage_errors = fields.List(
        fields.String,
        example=[],
        description="A collection of general stage errors",
    )


class QuickSetupButton(BaseSchema):
    id = fields.String(
        example="next",
        description="The button id",
        allow_none=True,
    )
    label = fields.String(
        example="Next",
        description="The label of the button",
    )
    aria_label = fields.String(
        example="Next",
        description="The aria label of the button",
        allow_none=True,
    )


class Action(BaseSchema):
    id = fields.String(
        example="action",
        description="The action id",
    )
    button = fields.Nested(
        QuickSetupButton,
        example={"label": "Next", "aria_label": "Next"},
        description="Definition of the action button",
    )
    load_wait_label = fields.String(
        example="Please wait...",
        description="A string to display while waiting for the next stage",
    )


class QuickSetupNextStageStructure(BaseSchema):
    components = fields.List(
        fields.Dict,
        example=[],
        description="A collection of stage components",
    )
    actions = fields.List(
        fields.Nested(Action),
        example=[],
        description="A collection of stage actions",
    )
    prev_button = fields.Nested(
        QuickSetupButton,
        example={"id": "prev", "label": "Back"},
        description="Definition of the `go to previous stage` button",
        allow_none=True,
    )


class QuickSetupStageResponse(BaseSchema):
    stage_recap = fields.List(
        fields.Dict,
        example=[],
        description="A collection of widget recaps",
    )
    next_stage_structure = fields.Nested(
        QuickSetupNextStageStructure,
        example={"components": [], "button_label": "", "prev_button_label": ""},
        description="The next stage structure",
    )
    errors = fields.Nested(
        Errors,
        example={},
        description="All formspec errors and general stage errors",
        allow_none=True,
    )


class QuickSetupCompleteStageResponse(BaseSchema):
    title = fields.String(
        example="Prepare AWS for Checkmk",
        description="The title of a stage",
    )
    sub_title = fields.String(
        example="aws",
        description="The sub-title of a stage",
        allow_none=True,
    )
    components = fields.List(
        fields.Dict,
        example=[],
        description="A collection of stage components",
    )
    actions = fields.List(
        fields.Nested(Action),
        example=[],
        description="A collection of stage actions",
    )
    prev_button = fields.Nested(
        QuickSetupButton,
        example={"id": "prev", "label": "Back"},
        description="Definition of the `go to previous stage` button",
        allow_none=True,
    )


class QuickSetupBaseResponse(BaseSchema):
    quick_setup_id = fields.String(
        example="aws_quicksetup",
        description="The quicksetup id",
    )
    actions = fields.List(
        fields.Nested(Action),
        example=[{"id": "save", "label": "Save configuration"}],
        description="A list of all complete actions",
    )

    prev_button = fields.Nested(
        QuickSetupButton,
        example={"id": "prev", "label": "Back", "aria_label": "Back"},
        description="Definition of the `go to previous stage` button",
        allow_none=True,
    )

    guided_mode_string = fields.String(
        example="Guided mode",
        description="The string for the guided mode label",
    )

    overview_mode_string = fields.String(
        example="Overview mode",
        description="The string for the overview mode label",
    )


class QuickSetupOverviewResponse(QuickSetupBaseResponse):
    stages = fields.List(
        fields.Nested(QuickSetupCompleteStageResponse),
        example=[],
        description="A list of all stages and their components",
    )


class QuickSetupGuidedResponse(QuickSetupBaseResponse):
    overviews = fields.List(
        fields.Nested(QuickSetupStageOverviewResponse),
        example=[],
        description="The overview of the quicksetup stages",
    )
    stage = fields.Nested(
        QuickSetupStageResponse,
        example={"components": []},
        description="The first stage",
    )


class QuickSetupResponse(OneOfSchema):
    type_field = "mode"
    type_field_remove = True
    type_schemas = {
        "guided": QuickSetupGuidedResponse,
        "overview": QuickSetupOverviewResponse,
    }

    def get_obj_type(self, obj):
        mode = obj.get("mode")
        if mode in self.type_schemas:
            return mode

        raise Exception("Unknown object type: %s" % repr(obj))


class QuickSetupCompleteResponse(BaseSchema):
    redirect_url = fields.String(
        example="http://save/url",
        description="The url to redirect to after saving the quicksetup",
    )

    all_stage_errors = fields.List(
        fields.Nested(
            Errors,
            example={},
            description="Formspec errors and general stage errors",
            allow_none=True,
        ),
        description="A list of stage errors",
        example=[],
    )
