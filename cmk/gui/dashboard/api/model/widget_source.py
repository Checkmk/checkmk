#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from typing import Annotated, Literal

from pydantic import AwareDatetime

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.type_defs import VisualContext

from .widget_content._base import BaseWidgetContent


@api_model
class ExplicitWidgetContent[C: BaseWidgetContent]:
    type: Literal["explicit"] = api_field(
        description="The caller sends the widget configuration and its filter context."
    )
    content: C = api_field(description="The widget configuration.")
    context: VisualContext = api_field(description="The effective filter context of the widget.")


@api_model
class SavedWidgetContent:
    type: Literal["saved"] = api_field(
        description="The widget is read from the dashboard that the token was issued for."
    )
    widget_id: str = api_field(
        description="The ID of the widget on the token's dashboard.", example="widget_1"
    )


@api_model
class WidgetTimeRange:
    start: Annotated[dt.datetime, AwareDatetime] = api_field(
        description="The start of the time range.", example="2026-01-01T00:00:00Z"
    )
    end: Annotated[dt.datetime, AwareDatetime] = api_field(
        description="The end of the time range.", example="2026-01-01T01:00:00Z"
    )

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ValueError("The start of the time range must be before its end.")

    def as_epoch_range(self) -> tuple[int, int]:
        """The start and the end in Unix epoch seconds."""
        return int(self.start.timestamp()), int(self.end.timestamp())
