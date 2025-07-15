#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.regex import GROUP_NAME_PATTERN

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.endpoints.contact_group_config.common import InventoryPaths

from cmk import fields


class UpdateContactGroupAttributes(BaseSchema):
    alias = fields.String(
        example="Example Group",
        description="The name used for displaying in the GUI.",
        required=True,
    )
    inventory_paths = fields.Nested(
        InventoryPaths,
        required=False,
        description="Permitted HW/SW Inventory paths.",
        example={"type": "allow_all"},
    )
    customer = gui_fields.customer_field(
        required=False,
        should_exist=True,
        allow_global=True,
    )


class InputContactGroup(BaseSchema):
    """Creating a contact group"""

    name = gui_fields.GroupField(
        group_type="contact",
        example="OnCall",
        required=True,
        should_exist=False,
        description="The name of the contact group.",
        pattern=GROUP_NAME_PATTERN,
    )
    alias = fields.String(
        required=True,
        description="The name used for displaying in the GUI.",
        example="Not on Sundays.",
    )
    inventory_paths = fields.Nested(
        InventoryPaths,
        load_default=lambda: {"type": "allow_all"},
        description="Permitted HW/SW Inventory paths.",
        example={"type": "allow_all"},
    )
    customer = gui_fields.customer_field(
        required=True,
        should_exist=True,
        allow_global=True,
    )


class BulkInputContactGroup(BaseSchema):
    """Bulk creating contact groups"""

    # TODO: add unique entries attribute
    entries = fields.List(
        fields.Nested(InputContactGroup),
        example=[
            {
                "name": "OnCall",
                "alias": "Not on Sundays",
            }
        ],
        uniqueItems=True,
        description="A collection of contact group entries.",
        required=True,
    )


class UpdateContactGroup(BaseSchema):
    """Updating a contact group"""

    name = gui_fields.GroupField(
        group_type="contact",
        description="The name of the contact group.",
        example="OnCall",
        required=True,
        should_exist=True,
    )
    attributes = fields.Nested(
        UpdateContactGroupAttributes,
        required=True,
    )


class BulkUpdateContactGroup(BaseSchema):
    """Bulk update contact groups"""

    entries = fields.List(
        fields.Nested(UpdateContactGroup),
        example=[
            {
                "name": "OnCall",
                "attributes": {
                    "alias": "Not on Sundays",
                },
            }
        ],
        description="A list of contact group entries.",
        required=True,
    )


class BulkDeleteContactGroup(BaseSchema):
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the contact group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
        description="A list of contract group names.",
    )
