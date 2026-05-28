#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class QuickSetupStageRequestModel:
    form_data: dict[str, Any] = api_field(
        description="The form data entered by the user.", example={}
    )


@api_model
class QuickSetupStageActionRequestModel:
    stage_action_id: str = api_field(
        description="The id of the stage action to be performed", example="test_connection"
    )
    stages: list[QuickSetupStageRequestModel] = api_field(
        description="A list of stages",
        example=[{"form_data": {}}, {"form_data": {}}],
        default_factory=list,
    )


@api_model
class QuickSetupFinalActionRequestModel:
    button_id: str = api_field(
        description="Unique id of the action button clicked by the user", example="save"
    )
    stages: list[QuickSetupStageRequestModel] = api_field(
        description="A list of stages' form data",
        example=[{"stage_data": []}, {"stage_data": []}],
        default_factory=list,
    )
