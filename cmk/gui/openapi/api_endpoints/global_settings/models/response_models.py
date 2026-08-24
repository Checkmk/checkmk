#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class GlobalSettingModel:
    varname: str = api_field(
        description="The internal name of the configuration variable.",
        example="log_levels",
    )
    value: object = api_field(
        description="The value of the configuration variable.",
        example={"cmk.web": 20},
    )
    is_default: bool = api_field(
        description="True if no value is configured for this variable. "
        "Configuring a value makes this false "
        "even if the configured value is identical to the default.",
        example=True,
    )


@api_model
class SiteGlobalSettingModel(GlobalSettingModel):
    site_id: str = api_field(
        description="The ID of the site connection this value belongs to.",
        example="prod",
    )
    is_default: bool = api_field(
        description="True if this site connection does not override the variable, so that "
        "`value` shows the central value - or the built-in default, if the variable is "
        "unset centrally as well. Those two cases are not distinguished here.",
        example=True,
    )
