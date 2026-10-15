#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Translate map JSON written in an earlier spelling to the current wire shape.

The daemon runs these on every map it validates, so a stored map keeps loading.
The legacy maps update action runs the same translation before it hands a
board to the REST API, which does not translate.
"""


def accept_legacy_backend_id(data: object) -> object:
    """Move the pre-rename ``backend_id`` key to ``connection_id``, in place."""
    if isinstance(data, dict) and "backend_id" in data and "connection_id" not in data:
        data["connection_id"] = data.pop("backend_id")
    return data


def migrate_weathermap(data: object) -> object:
    """Split ``line_style: weathermap`` into its three aspects, in place.

    The old style bundled the bidirectional shape, the bandwidth label and
    the utilization gradient.
    """
    if isinstance(data, dict) and data.get("line_style") == "weathermap":
        data["line_style"] = "arrow_inward"
        data.setdefault("line_perfdata_label", "bandwidth")
        data.setdefault("line_weather_color", True)
    return data


def coerce_graph_metric(value: object) -> list[str] | None:
    """Read ``graph_metric`` as the list it is today; older maps hold one string."""
    if isinstance(value, str):
        return [value] if value else None
    if isinstance(value, list):
        return [s for s in value if isinstance(s, str)]
    return None
