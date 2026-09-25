#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from pydantic import Discriminator

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.type_defs import FilterName

from .contextual_link import VisualLocation


@api_model
class ResolvedLink:
    title: str = api_field(description="The title of the link.")
    location: VisualLocation = api_field(description="The target visual.")
    include_context: bool = api_field(
        description="Whether the link carries the widget's effective filter context."
    )
    include_time_range: bool = api_field(
        description="Whether the link carries the dashboard's time range."
    )
    show_filter_form: bool = api_field(
        description="Whether the target opens with its filter form shown."
    )


@api_model
class EncodedFilter:
    status: Literal["encoded"] = api_field(description="The filter travels with the link.")
    variables: dict[str, str] = api_field(
        description="The HTTP variables that carry the filter to the target."
    )


@api_model
class DroppedFilter:
    status: Literal["dropped"] = api_field(description="The filter does not travel with the link.")
    reason: Literal["no_value", "no_such_key", "not_available"] = api_field(
        description="Why the filter does not travel."
    )


type FilterResult = Annotated[EncodedFilter | DroppedFilter, Discriminator("status")]


@api_model
class LinkProperties:
    links: list[dict[FilterName, FilterResult]] = api_field(
        description="One map of filter results per resolved link, in the order of the links."
    )
