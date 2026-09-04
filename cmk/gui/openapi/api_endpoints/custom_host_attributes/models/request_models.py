#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class CreateCustomHostAttrModel:
    name: str = api_field(
        description="A unique name for the attribute. Cannot be changed after creation.",
        example="coordinates",
        pattern=r"^[-a-z0-9A-Z_]+$",
    )
    title: str = api_field(
        description="A human-readable title for the attribute.",
        example="Coordinates",
    )
    data_type: Literal["TextAscii"] = api_field(
        description="The data type of the attribute. Currently only simple text is supported.",
        example="TextAscii",
        default="TextAscii",
    )
    topic: str = api_field(
        description="The internal ID of the section this attribute appears in when editing a host.",
        example="custom_attributes",
        default="custom_attributes",
    )
    help: str = api_field(
        description="A help text shown next to the attribute in the UI.",
        example="GPS coordinates of the host location.",
        default="",
    )
    show_in_table: bool = api_field(
        description="Show this attribute in host tables in the Setup menu.",
        example=False,
        default=False,
    )
    add_custom_macro: bool = api_field(
        description=(
            "Make this attribute available to check commands, notifications and the "
            "status GUI as a custom macro."
        ),
        example=False,
        default=False,
    )


@api_model
class UpdateCustomHostAttrModel:
    title: str | None = api_field(
        description="A human-readable title for the attribute.",
        example="Coordinates",
        default=None,
    )
    topic: str | None = api_field(
        description="The internal ID of the section this attribute appears in when editing a host.",
        example="custom_attributes",
        default=None,
    )
    help: str | None = api_field(
        description="A help text shown next to the attribute in the UI.",
        example="GPS coordinates of the host location.",
        default=None,
    )
    show_in_table: bool | None = api_field(
        description="Show this attribute in host tables in the Setup menu.",
        example=False,
        default=None,
    )
    add_custom_macro: bool | None = api_field(
        description=(
            "Make this attribute available to check commands, notifications and the "
            "status GUI as a custom macro."
        ),
        example=False,
        default=None,
    )
