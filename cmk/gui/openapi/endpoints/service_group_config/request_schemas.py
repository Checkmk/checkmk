#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk import fields
from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.utils.regex import GROUP_NAME_PATTERN

EXISTING_SERVICE_GROUP_NAME = gui_fields.GroupField(
    group_type="service",
    example="windows",
    required=True,
    description="The name of the service group.",
    should_exist=True,
)


class InputGroup(BaseSchema):
    customer = gui_fields.customer_field(
        required=True,
        should_exist=True,
        allow_global=True,
    )


class InputServiceGroup(InputGroup):
    """Creating a service group"""

    name = gui_fields.GroupField(
        group_type="service",
        example="windows",
        required=True,
        description="A name used as identifier",
        should_exist=False,
        pattern=GROUP_NAME_PATTERN,
    )
    alias = fields.String(
        description="The name used for displaying in the GUI.",
        example="Environment Sensors",
        required=True,
    )


class BulkInputServiceGroup(BaseSchema):
    """Bulk creating service groups"""

    entries = fields.List(
        fields.Nested(InputServiceGroup),
        example=[
            {
                "name": "environment",
                "alias": "Environment Sensors",
            }
        ],
        uniqueItems=True,
        description="A list of service group entries.",
        required=True,
    )


class UpdateServiceGroupAttributes(BaseSchema):
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


class UpdateServiceGroup(BaseSchema):
    """Updating a service group"""

    name = EXISTING_SERVICE_GROUP_NAME
    attributes = fields.Nested(
        UpdateServiceGroupAttributes,
        required=True,
    )


class BulkUpdateServiceGroup(BaseSchema):
    """Bulk update service groups"""

    entries = fields.List(
        fields.Nested(UpdateServiceGroup),
        example=[
            {
                "name": "windows",
                "attributes": {
                    "alias": "Windows Servers",
                },
            }
        ],
        description="A list of service group entries.",
        required=True,
    )


class BulkDeleteServiceGroup(BaseSchema):
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the service group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
        description="A list of service group names.",
    )
