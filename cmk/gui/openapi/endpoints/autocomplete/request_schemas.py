#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from marshmallow import INCLUDE, ValidationError

from cmk.gui.fields.utils import BaseSchema

from cmk import fields


class BoolOrStringField(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, bool | str):
            return value

        raise ValidationError("Invalid type. Expected bool or str.")


class ParamsSchema(BaseSchema):
    class Meta:
        unknown = INCLUDE

    strict = BoolOrStringField(
        metadata={
            "description": "Whether to use strict matching",
            "example": True,
        },
        required=False,
    )
    group_type = fields.String(
        description="The group type",
        example="host",
        required=False,
    )
    group_id = fields.String(
        description="The group id",
        example="my_group",
        required=False,
    )
    world = fields.String(
        description="World field",
        example="Earth",
        required=False,
    )
    presentation = fields.String(
        description="Presentation field",
        example="lines",
        required=False,
    )
    mode = fields.String(
        description="Mode field",
        example="template",
        required=False,
    )
    datasource = fields.String(
        description="Datasource field",
        example="services",
        required=False,
    )
    single_infos = fields.List(
        fields.String,
        description="Single infos field",
        example=["my_info"],
        required=False,
    )


class RequestSchema(BaseSchema):
    value = fields.String(
        description="Value used for filtering autocomplete results",
        example="central_site",
        required=False,
        load_default="",
    )

    parameters = fields.Nested(
        ParamsSchema,
        description="Parameters related to the autocompleter being invoked",
        required=False,
        example={"strict": False, "context": {}},
    )
