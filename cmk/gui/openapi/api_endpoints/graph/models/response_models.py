#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class MetricNameMappingResponse:
    metric_names: dict[str, str] = api_field(
        description=(
            "The canonical metric name each of the service's raw perf-data names is known by, "
            "keyed by the raw name. A name no plug-in renames maps to itself, so every name the "
            "service reports has an entry. Empty when the host or service is not monitored, or "
            "when it reports no perf data at all."
        ),
        example={"wait": "io_wait", "user": "user"},
    )
