#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.regex import GROUP_NAME_PATTERN

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema

from cmk import fields

EXISTING_HOST_GROUP_NAME = gui_fields.GroupField(
    group_type="host",
    example="windows",
    required=True,
    description="The name of the host group.",
    should_exist=True,
)


class InputGroup(BaseSchema):
    customer = gui_fields.customer_field(
        required=True,
        should_exist=True,
        allow_global=True,
    )


class InputHostGroup(InputGroup):
    """Creating a host group"""

    name = gui_fields.GroupField(
        group_type="host",
        example="windows",
        required=True,
        should_exist=False,
        description="A name used as identifier",
        pattern=GROUP_NAME_PATTERN,
    )
    alias = fields.String(
        required=True,
        description="The name used for displaying in the GUI.",
        example="Windows Servers",
    )


class BulkInputHostGroup(BaseSchema):
    """Bulk creating host groups"""

    entries = fields.List(
        fields.Nested(InputHostGroup),
        example=[
            {
                "name": "windows",
                "alias": "Windows Servers",
            }
        ],
        uniqueItems=True,
        description="A list of host group entries.",
        required=True,
    )


class UpdateHostGroupAttributes(BaseSchema):
    alias = fields.String(
        example="Example Group",
        description="The name used for displaying in the GUI.",
        required=True,
    )
    customer = gui_fields.customer_field(
        required=False,
        should_exist=True,
        allow_global=True,
    )


class UpdateHostGroup(BaseSchema):
    """Updating a host group"""

    name = EXISTING_HOST_GROUP_NAME
    attributes = fields.Nested(
        UpdateHostGroupAttributes,
        required=True,
    )


class BulkUpdateHostGroup(BaseSchema):
    """Bulk update host groups"""

    entries = fields.List(
        fields.Nested(UpdateHostGroup),
        example=[
            {
                "name": "windows",
                "attributes": {
                    "alias": "Windows Servers",
                },
            }
        ],
        description="A list of host group entries.",
        required=True,
    )


class BulkDeleteHostGroup(BaseSchema):
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the host group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
        description="A list of host group names.",
    )
