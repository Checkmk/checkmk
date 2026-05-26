#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)


@api_model
class CustomHostAttrExtensions:
    topic: str = api_field(
        description="The section this attribute appears in when editing a host.",
        example="Custom attributes",
    )
    help: str = api_field(
        description="A help text shown next to the attribute in the UI.",
        example="GPS coordinates of the host location.",
    )
    show_in_table: bool = api_field(
        description="Whether this attribute is shown in host tables in the Setup menu.",
        example=False,
    )
    add_custom_macro: bool = api_field(
        description="Whether this attribute is available as a custom macro.",
        example=False,
    )


@api_model
class CustomHostAttrObject(DomainObjectModel):
    domainType: Literal["custom_host_attribute"] = api_field(
        description="The domain type of the object.",
    )
    extensions: CustomHostAttrExtensions = api_field(
        description="The attributes of the custom host attribute.",
    )


@api_model
class CustomHostAttrCollection(DomainObjectCollectionModel):
    domainType: Literal["custom_host_attribute"] = api_field(
        description="The domain type of the objects in the collection.",
    )
    value: list[CustomHostAttrObject] = api_field(
        description="A list of custom host attribute objects.",
        example=[],
    )
