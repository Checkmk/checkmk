#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class AutocompleteRequestModel:
    value: str = api_field(
        description="Value used for filtering autocomplete results",
        example="central_site",
        default="",
    )
    parameters: dict[str, object] = api_field(
        description="Parameters related to the autocompleter being invoked",
        default_factory=dict,
    )
