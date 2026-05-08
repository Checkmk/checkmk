#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

import datetime as dt
from typing import Annotated, Literal

from pydantic import Discriminator

from cmk.ccc.site import SiteId
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName


@api_model
class FixedDowntimeModeModel:
    type: Literal["fixed"] = api_field(
        description="The downtime is fixed to the start and end time.",
        example="fixed",
    )


@api_model
class FlexibleDowntimeModeModel:
    type: Literal["flexible"] = api_field(
        description=(
            "The downtime starts if the host or service goes down during the specified start and "
            "end time window. It will then last for at most the given duration, which can extend "
            "past the end time."
        ),
        example="flexible",
    )
    duration_minutes: int = api_field(
        description="The flexible duration in minutes.",
        example=120,
    )


type DowntimeModeModel = Annotated[
    FixedDowntimeModeModel | FlexibleDowntimeModeModel, Discriminator("type")
]


@api_model
class DowntimeExtensionsModel:
    site_id: SiteId = api_field(description="The site id of the downtime.", example="mysite")
    host_name: AnnotatedHostName = api_field(description="The host name.", example="cmk.abc.ch")
    author: str = api_field(description="The author of the downtime.", example="Mr Bojangles")
    is_service: bool = api_field(
        description="Whether the downtime is for a service.",
        example=False,
    )
    start_time: dt.datetime = api_field(
        description="The start time of the downtime.",
        example="2023-08-04T08:58:01+00:00",
    )
    end_time: dt.datetime = api_field(
        description="The end time of the downtime.",
        example="2023-08-04T09:18:01+00:00",
    )
    recurring: bool = api_field(
        description="Indicates if this downtime is time-repetitive",
        example=True,
    )
    comment: str = api_field(description="A comment text.", example="Down for update")
    mode: DowntimeModeModel = api_field(
        description="The mode of the downtime, either fixed or flexible.",
        example={"type": "flexible", "duration_minutes": 120},
    )
    service_description: str | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        description=(
            "The service name if the downtime corresponds to a service, "
            "otherwise this field is not present."
        ),
        example="CPU Load",
    )


@api_model
class DowntimeObjectModel(DomainObjectModel):
    domainType: Literal["downtime"] = api_field(description="The domain type of the object.")
    extensions: DowntimeExtensionsModel = api_field(description="The attributes of a downtime.")


@api_model
class DowntimeCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["downtime"] = api_field(
        description="The domain type of the objects in the collection."
    )
    value: list[DowntimeObjectModel] = api_field(
        description="A list of downtime objects.",
        example=[],
    )
