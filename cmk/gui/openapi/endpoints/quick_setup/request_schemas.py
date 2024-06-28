#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.fields.utils import BaseSchema

from cmk import fields


class QuickSetupStageRequest(BaseSchema):
    stage_id = fields.Integer(
        required=True,
        example=1,
        description="The id of the stage.",
    )
    form_data = fields.Dict(
        required=True,
        example={},
        description="The form data entered by the user.",
    )


class QuickSetupRequest(BaseSchema):
    quick_setup_id = fields.String(
        required=True,
        description="The quick setup id",
        example="aws",
    )

    stages = fields.List(
        fields.Nested(
            QuickSetupStageRequest,
            required=True,
            description="A stage id and its components",
        ),
        example=[{"stage_id": 1, "form_data": {}}, {"stage_id": 2, "form_data": {}}],
        description="A list of stages",
    )


class QuickSetupFinalSaveRequest(BaseSchema):
    stages = fields.List(
        fields.Nested(
            QuickSetupStageRequest,
            required=True,
            description="A stage id and it's form data",
        ),
        example=[
            {"stage_id": 1, "stage_data": []},
            {"stage_id": 2, "stage_data": []},
        ],
        description="A list of stages' form data",
    )
