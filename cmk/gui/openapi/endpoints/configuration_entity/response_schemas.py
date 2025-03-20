#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.fields.base import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject

from cmk import fields


class ValidationMessage(BaseSchema):
    location = fields.List(
        fields.String,
        example=[],
        description="Location of the error",
    )
    message = fields.String(
        example="",
        description="Error message",
    )
    replacement_value = fields.String(
        example="",
        description="Invalid value",
    )


class ResponseData(BaseSchema):
    validation_errors = fields.List(
        fields.Nested(ValidationMessage),
        example=[],
        description="All form spec validation errors",
        allow_none=True,
    )


class EditConfigurationEntityResponse(DomainObject):
    domainType = fields.Constant(
        "configuration_entity", description="Domain type of the configuration entity"
    )
    extensions = fields.Nested(ResponseData, description="Response data for entity creation")
