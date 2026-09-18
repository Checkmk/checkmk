#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from annotated_types import Ge

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)


@api_model
class GraphTimerangeExtension:
    sort_index: Annotated[int, Ge(ge=0)] = api_field(
        example=1,
        description="The index of the graph timerange for sorting multiple entries.",
    )
    total_seconds: Annotated[int, Ge(ge=0)] = api_field(
        example=14400,
        description="The total duration of the graph timerange in seconds.",
    )


@api_model
class GraphTimerangeObject(DomainObjectModel):
    domainType: Literal["graph_timerange"] = api_field(
        description="The type of the domain-object.",
    )
    extensions: GraphTimerangeExtension = api_field(
        description="All the attributes of the domain object.",
    )


@api_model
class GraphTimerangeCollection(DomainObjectCollectionModel):
    domainType: Literal["graph_timerange"] = api_field(
        description="The domain type of the objects in the collection.",
    )
    value: list[GraphTimerangeObject] = api_field(
        description="A list of GraphTimerange objects.",
    )
