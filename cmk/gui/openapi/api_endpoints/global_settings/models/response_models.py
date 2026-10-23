#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.watolib.global_settings import GlobalSettingsOrigin


@api_model
class GlobalSettingModel:
    varname: str = api_field(
        description="The internal name of the configuration variable.",
        example="log_levels",
    )
    value: object = api_field(
        description="The value of the configuration variable, values not masked.",
        example={"cmk.web": 20},
    )
    spec: object = api_field(
        description="The form the GUI renders and edits the value with. Choices that "
        "refer to configuration objects, e.g. stored passwords, list the ones existing "
        "at the time of the request.",
        example={"type": "dictionary", "title": "Logging"},
    )
    origin: GlobalSettingsOrigin = api_field(
        description="The layer the value comes from: `global` once a value is configured "
        "centrally, `factory` while none is, even if the configured value is identical "
        "to the built-in default.",
        example=GlobalSettingsOrigin.factory.value,
    )


@api_model
class SiteGlobalSettingModel(GlobalSettingModel):
    site_id: str = api_field(
        description="The ID of the site connection this value belongs to.",
        example="prod",
    )
    origin: GlobalSettingsOrigin = api_field(
        description="The layer the value comes from: `site` when this site connection "
        "overrides the variable, `global` when it inherits a centrally configured value, "
        "`factory` when neither configures one.",
        example=GlobalSettingsOrigin.site.value,
    )
