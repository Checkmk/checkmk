#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.fields.utils import BaseSchema

from cmk import fields


class QuickSetupStageOverviewResponse(BaseSchema):
    stage_id = fields.Integer(
        example=1,
        description="The id of the stage.",
    )
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
    formspec_errors = fields.Dict(
        example={},
        description="A mapping of formspec ids to formspec validation errors",
    )
    stage_errors = fields.List(
        fields.String,
        example=[],
        description="A collection of general stage errors",
    )


class QuickSetupStageResponse(BaseSchema):
    stage_id = fields.Integer(
        example=1,
        description="The id of the stage.",
    )
    components = fields.List(
        fields.Dict,
        example=[],
        description="A collection of stage components",
    )
    errors = fields.Nested(
        Errors,
        example={},
        description="All formspec errors and general stage errors",
        allow_none=True,
    )
    stage_recap = fields.List(
        fields.Dict,
        example=[],
        description="A collection of widget recaps",
    )
    button_txt = fields.String(
        example="Next",
        description="The text of the button",
        allow_none=True,
    )


class QuickSetupOverviewResponse(BaseSchema):
    quick_setup_id = fields.String(
        example="aws_quicksetup",
        description="The quicksetup id",
    )
    overviews = fields.List(
        fields.Nested(QuickSetupStageOverviewResponse),
        example=[],
        description="The overview of the quicksetup stages",
    )
    stage = fields.Nested(
        QuickSetupStageResponse,
        example={"stage_id": 1, "components": []},
        description="The first stage",
    )


class QuickSetupSaveResponse(BaseSchema):
    redirect_url = fields.String(
        example="http://save/url",
        description="The url to redirect to after saving the quicksetup",
    )
