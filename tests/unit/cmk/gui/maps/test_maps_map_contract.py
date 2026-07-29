#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The Maps map-shape contract, pinned end to end.

The map payload has two typed representations: the daemon's pydantic
``cmk.maps.backend.schemas.map.MapConfig`` (the shape *validation* source of
truth, a *flat* model applied to every map the daemon serves) and the REST-API
``@api_model`` mirror (``cmk.maps.rest_api.models.map.MapConfig``), which *groups*
the object fields into nested sub-objects and is the source the frontend
TypeScript types are generated from. The two shapes are bridged by
``cmk.maps.rest_api.utils.map_from_spec`` / ``spec_from_map`` (flat store <->
grouped API), the ``from_internal``/``to_internal`` equivalent.

This test feeds the *same* representative maps through that bridge and asserts a
full round-trip (flat daemon dump -> grouped REST model -> flattened back ->
daemon parse), so a renamed/removed/retyped/regrouped field on either side — or a
mismapped bridge entry — fails CI.
"""

import pytest
from pydantic import ValidationError

from cmk.maps.backend.schemas.map import MapConfig as DaemonMapConfig
from cmk.maps.rest_api.models.map import MapObjectBinding
from cmk.maps.rest_api.utils import map_from_spec, spec_from_map
from cmk.maps.shared.map_payload import MapPayload

# Representative maps exercising every discriminated-union branch (all view
# types across the two, plus each presentation element kind) and a spread of
# object/label fields — the parts most prone to silent drift.
_FLOW_MAP: dict[str, object] = {
    "name": "dc-muc",
    "alias": "Datacenter Munich",
    "connection_id": "live_1",
    "default_z": 10,
    "view": {
        "type": "flow",
        "root": "srv1",
        "child_layers": 2,
        "positions": {"srv1": {"x": 1.0, "y": 2.0}},
        "service_layout": "donut",
    },
    "objects": [
        {
            "id": "o1",
            "type": "host",
            "host_name": "srv1",
            "x": 10,
            "y": 20,
            "label": {"show": True, "text": "web", "size": 12},
            "display": {"mode": "gadget", "gadget_type": "gauge", "gadget_metric": "load"},
        },
        {
            "id": "o2",
            "type": "line",
            "start_ref": "o1",
            "line_style": "arrow_end",
            "line_perfdata_label": "bandwidth",
            "weathermap_metric": "if_in",
        },
    ],
}

_WORLDMAP_MAP: dict[str, object] = {
    "name": "world",
    "view": {"type": "worldmap", "lat": 51.0, "lng": 10.0, "zoom": 5, "auto_source": "all_hosts"},
    "objects": [{"id": "h1", "type": "host", "host_name": "srv1", "lat": 48.1, "lng": 11.6}],
}

_FOLDERTREE_MAP: dict[str, object] = {
    "name": "folders",
    "view": {"type": "foldertree", "root_folder": "", "sites": ["central"], "show_services": True},
}

_RADAR_MAP: dict[str, object] = {
    "name": "radar",
    "view": {"type": "radar", "filter": "hostgroup", "filter_value": "linux"},
}

_STATIC_MAP: dict[str, object] = {
    "name": "static",
    "view": {"type": "static", "problems_only": True},
    "objects": [{"id": "t1", "type": "textbox", "textbox_width": 120}],
}

_PRESENTATION_MAP: dict[str, object] = {
    "name": "slide1",
    "view": {
        "type": "presentation",
        "width": 1920,
        "height": 1080,
        "theme": "midnight",
        "elements": [
            {"kind": "shape", "id": "s1", "shape": "rect", "fill": "#3b82f6", "flow": True},
            {"kind": "text", "id": "t1", "text": "Title", "font_size": 24},
            {"kind": "image", "id": "i1", "src": "/logo.png", "fit": "contain"},
            {"kind": "data", "id": "d1", "host_name": "srv1", "display": {"mode": "icon"}},
            {"kind": "group", "id": "g1", "children": ["s1", "t1"]},
        ],
    },
}

_MAPS = [
    _FLOW_MAP,
    _WORLDMAP_MAP,
    _FOLDERTREE_MAP,
    _RADAR_MAP,
    _STATIC_MAP,
    _PRESENTATION_MAP,
]


@pytest.mark.parametrize("map_spec", _MAPS)
def test_rest_model_accepts_and_round_trips_to_daemon(map_spec: dict[str, object]) -> None:
    # The REST model requires the structural fields the daemon defaults, so densify
    # via the daemon first; grouping into the REST model and flattening back out
    # must still yield a valid daemon map.
    dense = DaemonMapConfig.model_validate(map_spec).model_dump(mode="json")
    rest_obj = map_from_spec(dense)
    DaemonMapConfig.model_validate(spec_from_map(rest_obj))


@pytest.mark.parametrize("map_spec", _MAPS)
def test_daemon_dense_map_is_accepted_by_rest_model(map_spec: dict[str, object]) -> None:
    # A dense map (all daemon defaults filled) must group cleanly into the REST
    # model — catches a field the daemon has but the REST mirror is missing or
    # a bridge entry that points at the wrong stored key.
    dense = DaemonMapConfig.model_validate(map_spec).model_dump(mode="json")
    map_from_spec(dense)


@pytest.mark.parametrize(
    "field", ["line_color", "label_border", "textbox_background", "textbox_border"]
)
def test_rest_model_rejects_css_injection_color(field: str) -> None:
    # Defense in depth at the REST write boundary: a CSS-injection color must be
    # rejected before it can be stored and served to the SPA (which also escapes
    # it at the render sink). Mirrors the daemon-side color validation.
    dense = DaemonMapConfig.model_validate(_WORLDMAP_MAP).model_dump(mode="json")
    dense["objects"][0][field] = '#fff" onmouseover="alert(1)'
    with pytest.raises(ValidationError):
        map_from_spec(dense)


def test_rest_model_rejects_object_filter_without_filter_header() -> None:
    # Mirrors the daemon's object_filter validation: a dyngroup filter that is not
    # safe ``Filter:`` combinator lines must be rejected at the REST write boundary.
    # Without this the store persists a filter the daemon later rejects on register,
    # leaving the map permanently offline.
    dense = DaemonMapConfig.model_validate(_WORLDMAP_MAP).model_dump(mode="json")
    dense["objects"][0]["object_filter"] = "host_name ~ srv"
    with pytest.raises(ValidationError):
        map_from_spec(dense)


def test_rest_model_normalises_valid_object_filter() -> None:
    dense = DaemonMapConfig.model_validate(_WORLDMAP_MAP).model_dump(mode="json")
    dense["objects"][0]["object_filter"] = "Filter: host_name ~ srv"
    rest_obj = map_from_spec(dense)
    binding = rest_obj.objects[0].binding
    assert isinstance(binding, MapObjectBinding)
    assert binding.object_filter == "Filter: host_name ~ srv\n"


@pytest.mark.parametrize(
    "kind, field",
    [
        ("shape", "fill"),
        ("shape", "stroke"),
        ("text", "color"),
        ("data", "fill"),
    ],
)
def test_rest_model_rejects_css_injection_in_presentation_element_color(
    kind: str, field: str
) -> None:
    # The daemon validates the presentation-element colors too, so the REST mirror
    # must not be laxer: a CSS-injection color in a slide element has to be rejected
    # at the write boundary just like the map-label colors above.
    dense = DaemonMapConfig.model_validate(_PRESENTATION_MAP).model_dump(mode="json")
    element = next(e for e in dense["view"]["elements"] if e["kind"] == kind)
    element[field] = '#fff" onmouseover="alert(1)'
    with pytest.raises(ValidationError):
        map_from_spec(dense)


def test_imported_cfg_map_passes_the_rest_bridge(all_objects_map: MapPayload) -> None:
    """A parsed legacy .cfg map must satisfy the REST map model too.

    The SPA's import flow saves the parsed map through the create endpoint, so a
    schema mismatch (a missing ``sort_order``/``click_action``, an object without
    the required ``url_target``, or a partial ``label``) makes the save 400 and the
    import silently fail. ``cfg_to_map`` produces the flat stored shape, so it is
    validated through the same flat->grouped bridge the endpoint uses — for every
    object and line type the shared fixture covers.
    """
    map_from_spec(all_objects_map)
