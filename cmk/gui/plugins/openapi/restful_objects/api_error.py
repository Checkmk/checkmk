#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.fields.utils import BaseSchema

from cmk import fields


class ApiError(BaseSchema):
    """This is the base class for all API errors."""

    cast_to_dict = True

    status = fields.Integer(
        description="The HTTP status code.",
        required=True,
        example=404,
    )
    detail = fields.String(
        description="Detailed information on what exactly went wrong.",
        required=True,
        example="The resource could not be found.",
    )
    title = fields.String(
        description="A summary of the problem.",
        required=True,
        example="Not found",
    )
    _fields = fields.Dict(
        data_key="fields",  # mypy, due to attribute "fields" being used in marshmallow.Schema
        attribute="fields",
        keys=fields.String(description="The key name"),
        description="Detailed error messages on all fields failing validation.",
        required=False,
    )
    ext: fields.Field = fields.Dict(
        keys=fields.String(description="The key name"),
        description="Additional information about the error.",
        required=False,
    )
