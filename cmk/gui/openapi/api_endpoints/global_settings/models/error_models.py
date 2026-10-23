#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.api_endpoints.models.form_spec import FormSpecValidationErrorsModel
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.response import ApiErrorDataclass


@api_model
class GlobalSettingValidation422(ApiErrorDataclass):
    status: int = api_field(description="The HTTP status code.", example=422)
    title: str = api_field(
        description="A summary of the problem.",
    )
    detail: str = api_field(
        description="Detailed information on what exactly went wrong.",
    )
    ext: FormSpecValidationErrorsModel = api_field(
        description="Validation errors, so the frontend can render the error message next to the conflicting form element."
    )
