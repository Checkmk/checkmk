#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Request models for the Maps SPA's internal lookup endpoints.

Only the lookups whose input is structured or unbounded take a body; everything
addressable by a name or a handful of scalars stays a GET with query parameters.
"""

from typing import Annotated

from pydantic import Field

from cmk.gui.openapi.framework.model import api_field, api_model

# The SPA truncates deep BI trees for rendering; the server caps too so a crafted
# request cannot force an unbounded walk of the compiled aggregation.
MAX_TREE_DEPTH = 10


@api_model
class MapsMetricInfoRequest:
    perf_data: str = api_field(
        description="The raw perfdata string to resolve.",
        example="rta=0.5ms;200;500;0; pl=0%;80;100;;",
    )
    check_command: str = api_field(
        description="The check command that produced the perfdata; drives the metric translation.",
        example="check_mk_active-icmp",
        default="",
    )
    graphs: bool = api_field(
        description=(
            "Also resolve the applicable graph plug-ins. Requires the object "
            "context below — walking every registered plug-in is too costly for "
            "the per-tick Perf-O-Meter lookups that do not need it."
        ),
        default=False,
    )
    host_name: str = api_field(
        description="Host the perfdata belongs to. Required when ``graphs`` is set.",
        example="heute",
        default="",
    )
    service_description: str = api_field(
        description="Service the perfdata belongs to (empty for host perfdata).",
        example="CPU load",
        default="",
    )
    site_id: str = api_field(description="Site the object lives on.", example="heute", default="")


@api_model
class MapsAggregationTreeRequest:
    aggregation_id: str = api_field(
        description="The resolved BI aggregation (branch) name.", example="Host heute"
    )
    depth: Annotated[int, Field(ge=0, le=MAX_TREE_DEPTH)] = api_field(
        description="How many levels of the hierarchy to return.", example=2, default=2
    )


@api_model
class MapsAggregationStatesRequest:
    aggregation_ids: list[str] = api_field(
        description="Resolved BI aggregation names to compute the state for.",
        example=["Host heute"],
    )
