#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted


@api_model
class AutocompleteChoiceModel:
    id: str = api_field(description="The id of the choice.")
    value: str = api_field(description="The display value of the choice.")


@api_model
class AutocompleteResponseModel:
    choices: list[AutocompleteChoiceModel] = api_field(
        description="A list of choices.",
        example=[],
    )
    warning: str | ApiOmitted = api_field(
        description="An optional warning message to display to the user.",
        default_factory=ApiOmitted,
    )
