#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the daemon's map schema (validation/migration)."""

import pytest
from pydantic import ValidationError

from cmk.maps.backend.schemas.map import MapConfig, MapElement


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


def test_url_target_folds_unsafe_targets_to_blank() -> None:
    # _top / _parent (or a named frame) would let a click-through URL replace the
    # whole Checkmk UI with an external page, so anything but _blank/_self folds.
    for unsafe in ("_top", "_parent", "victimframe"):
        obj = MapElement.model_validate({"id": "o", "type": "host", "url_target": unsafe})
        assert obj.url_target == "_blank"


def test_url_target_keeps_safe_targets() -> None:
    for safe in ("_blank", "_self"):
        obj = MapElement.model_validate({"id": "o", "type": "host", "url_target": safe})
        assert obj.url_target == safe


def test_background_image_traversal_is_dropped() -> None:
    # background_image is a bare uploaded filename the SPA expands into an asset
    # URL; a path-traversal value must not survive to become a same-origin GET.
    cfg = MapConfig.model_validate({"name": "m", "background_image": "../../check_mk/logout.py"})
    assert cfg.background_image is None
    kept = MapConfig.model_validate({"name": "m", "background_image": "photo.png"})
    assert kept.background_image == "photo.png"


def test_image_src_bare_filename_is_kept() -> None:
    obj = MapElement.model_validate({"id": "o", "type": "host", "image_src": "icon.svg"})
    assert obj.image_src == "icon.svg"
    bad = MapElement.model_validate({"id": "o", "type": "host", "image_src": "../evil.svg"})
    assert bad.image_src is None


def test_custom_icon_traversal_is_dropped() -> None:
    # The custom icon wins over image_src in the SPA, so it needs the same guard.
    obj = MapElement.model_validate(
        {"id": "o", "type": "host", "display": {"image": "../../check_mk/logout.py"}}
    )
    assert obj.display is not None
    assert obj.display.image is None


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
