#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the daemon's map schema (validation/migration)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cmk.maps.backend.schemas.map import MapElement


def test_object_filter_without_filter_header_is_rejected() -> None:
    # A dyngroup filter must be safe ``Filter:`` combinator lines. Raw livestatus
    # column syntax (no header) is rejected so it can never reach the query path.
    with pytest.raises(ValidationError):
        MapElement.model_validate(
            {"id": "dg", "type": "dyngroup", "object_filter": "host_name ~ srv"}
        )


def test_object_filter_normalises_and_empty_becomes_none() -> None:
    obj = MapElement.model_validate(
        {"id": "dg", "type": "dyngroup", "object_filter": "Filter: host_name ~ srv"}
    )
    assert obj.object_filter == "Filter: host_name ~ srv\n"
    empty = MapElement.model_validate({"id": "dg2", "type": "dyngroup", "object_filter": "  "})
    assert empty.object_filter is None


def test_legacy_weathermap_style_migrates_to_arrow_inward() -> None:
    # A stored map with line_style='weathermap' must keep loading by
    # rewriting transparently to the orthogonal model on validation.
    obj = MapElement.model_validate(
        {
            "id": "line_legacy",
            "type": "line",
            "line_style": "weathermap",
            "host_name": "h",
            "service_description": "s",
        }
    )
    assert obj.line_style == "arrow_inward"
    assert obj.line_perfdata_label == "bandwidth"
    assert obj.line_weather_color is True
