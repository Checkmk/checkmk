#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from pydantic import StringConstraints

from cmk.gui.openapi.framework.model import api_field, api_model

type _ShortText = Annotated[str, StringConstraints(max_length=1024)]
type _UrlText = Annotated[str, StringConstraints(max_length=8192)]
type _LongText = Annotated[str, StringConstraints(max_length=64 * 1024)]


@api_model
class CreateJavascriptCrashReport:
    error_name: _ShortText = api_field(
        description="The name of the error caught in the browser.",
        example="TypeError",
    )
    error_message: _LongText = api_field(
        description="The message of the error caught in the browser.",
        example="Cannot read properties of undefined (reading 'title')",
    )
    url: _UrlText = api_field(
        description=(
            "The URL of the page the error occurred on. Generously sized, because a view "
            "or dashboard URL carries its whole filter context."
        ),
        example="http://localhost/heute/check_mk/dashboard.py",
    )
    stack: _LongText = api_field(
        description=(
            "The stack trace of the error, as reported by the browser. Frames without a "
            "source location are dropped."
        ),
        example="at renderTile (http://localhost/heute/check_mk/js/main.js:120:31)",
        default="",
    )
    component: _ShortText = api_field(
        description="The frontend component that caught the error.",
        example="DashboardApp",
        default="",
    )
    context: _LongText = api_field(
        description="Additional context the frontend collected about the error.",
        example="GET http://localhost/heute/check_mk/api/internal/version\nSTATUS 500",
        default="",
    )
