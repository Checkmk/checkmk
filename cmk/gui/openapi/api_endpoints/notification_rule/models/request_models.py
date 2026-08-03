#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted

_MOVE_POSITION_DESCRIPTION = (
    "The type of position to move the notification rule to. Notification rules are evaluated "
    "from top to bottom, so the rule with the lowest `rule_index` is evaluated first."
)


@api_model
class MoveNotificationRuleModel:
    position: Literal[
        "top_of_list", "bottom_of_list", "before_specific_rule", "after_specific_rule"
    ] = api_field(description=_MOVE_POSITION_DESCRIPTION, example="after_specific_rule")
    rule_id: str | ApiOmitted = api_field(
        description=(
            "The ID of the notification rule to move after/before. Required for the positions "
            "`before_specific_rule` and `after_specific_rule`."
        ),
        example="5425d554-5741-4bbf-b907-1a391dfab5bb",
        default_factory=ApiOmitted,
    )
