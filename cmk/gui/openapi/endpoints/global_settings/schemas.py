#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing

from marshmallow import ValidationError
from marshmallow_oneofschema import OneOfSchema

from cmk import fields
from cmk.gui.fields.base import BaseSchema


class GlobalSettingsOneOfSchema(OneOfSchema):
    type_field_remove = False
    type_field = "type"

    def get_obj_type(self, obj: dict[str, typing.Any]) -> str:
        if isinstance(obj, dict):
            if self.type_field not in obj:
                raise ValidationError(f"Object must have a {repr(self.type_field)} field")
            return obj[self.type_field]
        raise ValidationError(f"Invalid object type: {type(obj)} ({obj})")


class _IconBaseSchema(BaseSchema):
    type = fields.String(
        required=True,
        description="Icon enabled or disabled.",
        enum=["enabled", "disabled"],
        example="enabled",
    )


class _IconSchema(_IconBaseSchema):
    icon = fields.String(
        description="Icon",
        example="delete",
        required=True,
    )
    emblem = fields.String(
        description="Emblem",
        example="search",
        required=False,
    )


class IconSchema(GlobalSettingsOneOfSchema):
    type_schemas = {
        "enabled": _IconSchema,
        "disabled": _IconBaseSchema,
    }


class _CAInputBaseSchema(BaseSchema):
    type = fields.String(
        required=True,
        description="Use ca input or not.",
        enum=["enabled", "disabled"],
        example="enabled",
    )


class _CAInputSchemaEnabled(_CAInputBaseSchema):
    address = fields.String(description="Address", required=True)
    port = fields.Integer(description="Port", required=True, example=443)
    content = fields.String(description="Content", required=False)


class CAInputSchema(GlobalSettingsOneOfSchema):
    type_schemas = {
        "enabled": _CAInputSchemaEnabled,
        "disabled": _CAInputBaseSchema,
    }


class _FileUploadBaseSchema(BaseSchema):
    type = fields.String(
        required=True,
        description="Mode for uploading a file",
        enum=["raw", "file", "disabled"],
        example="file",
    )


class _FileUploadSchemaFile(_FileUploadBaseSchema):
    name = fields.String(
        description="Name",
        required=True,
        example="my_image.png",
    )
    mimetype = fields.String(
        description="Mimetype",
        required=True,
        example="image/png",
    )
    content = fields.String(
        description="Content",
        required=True,
    )


class _FileUploadSchemaRaw(_FileUploadBaseSchema):
    raw_value = fields.String(
        description="Raw value of a file",
        required=True,
    )


class FileUploadSchema(GlobalSettingsOneOfSchema):
    type_schemas = {
        "raw": _FileUploadSchemaRaw,
        "file": _FileUploadSchemaFile,
        "disabled": _FileUploadBaseSchema,
    }


class TagOneOfBaseSchema(BaseSchema):
    type = fields.String(
        enum=["is", "isnot", "ignore"],
        required=True,
        example="is",
    )
