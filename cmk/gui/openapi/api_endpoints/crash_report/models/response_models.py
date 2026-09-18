#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel


@api_model
class JavascriptCrashReportExtensions:
    crash_type: str = api_field(
        description="The type of the stored crash report.",
        example="javascript",
    )
    crash_report_url: str = api_field(
        description="The site local URL of the page showing the stored crash report.",
        example="crash.py?crash_id=dc9e0d0b-1b5b-11f0-8c1f-0242ac110002&site=heute",
    )


@api_model
class JavascriptCrashReportObjectModel(DomainObjectModel):
    domainType: Literal["javascript_crash_report"] = api_field(
        description="The domain type of the object.",
        example="javascript_crash_report",
    )
    extensions: JavascriptCrashReportExtensions = api_field(
        description="The metadata of the stored crash report."
    )
