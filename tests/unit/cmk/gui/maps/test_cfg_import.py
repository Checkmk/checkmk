#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the legacy .cfg map parser.

Covers the block tokenizer, NagVis coordinate parsing (incl. percent offsets and
two-segment line bends), and the full ``cfg_to_map`` conversion: global block,
host/service/line/shape/textbox/aggregation handling, line_type → line_style
mapping with template/global inheritance, weathermap metric defaults, url_target
frameset rewriting, and the geographic (worldmap/geomap) + container variants.

The "all objects" coverage runs off the shared ``all_objects_map`` fixture (see
``conftest.py``), an inlined NagVis map exercising every object and line type.
"""

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.maps.backend.schemas.map import MapConfig as DaemonMapConfig
from cmk.maps.gui import _cfg_import
from cmk.maps.gui._cfg_import import (
    _line_coords,
    _parse_blocks,
    _parse_coord,
    cfg_to_map,
    map_name_from_filename,
    resolve_connection_ids,
)
from cmk.maps.shared.map_payload import MapObject, MapPayload


def _coord(v: str) -> int:
    return _parse_coord(v).value


def test_parse_blocks_strips_hash_comments() -> None:
    text = "# top comment\ndefine global {\n    alias = Test\n}\n"
    blocks = _parse_blocks(text)
    assert len(blocks) == 1
    assert blocks[0][0] == "global"
    assert blocks[0][1]["alias"] == "Test"


def test_parse_blocks_strips_semicolon_comments() -> None:
    text = "; semicolon comment\ndefine host {\n    host_name = srv\n}\n"
    blocks = _parse_blocks(text)
    assert blocks[0][1]["host_name"] == "srv"


def test_parse_blocks_multiple_blocks() -> None:
    text = "define global {\n    alias = Map\n}\ndefine host {\n    host_name = h1\n}\n"
    blocks = _parse_blocks(text)
    assert len(blocks) == 2
    assert blocks[0][0] == "global"
    assert blocks[1][0] == "host"


def test_parse_blocks_unknown_type_included() -> None:
    text = "define futuretype {\n    key = value\n}\n"
    blocks = _parse_blocks(text)
    assert len(blocks) == 1
    assert blocks[0][0] == "futuretype"
    assert blocks[0][1]["key"] == "value"


def test_coord_integer() -> None:
    assert _coord("100") == 100
    assert _coord("  42  ") == 42


def test_coord_negative() -> None:
    assert _coord("-50") == -50


def test_coord_percent_is_resolved_against_the_nominal_canvas() -> None:
    # NagVis sizes a percent against the background image, which the text-only
    # import cannot measure, so it resolves against the SPA's nominal canvas
    # (1920x1080) — objects keep their relative layout instead of collapsing onto
    # the origin. The axis picks the dimension.
    assert _coord("50%") == 960
    assert _parse_coord("50%", "y").value == 540
    assert _coord("50%100") == 1060
    assert _coord("0%-50") == -50


def test_coord_bare_percent_is_not_read_as_a_reference() -> None:
    # Regression: a bare ``50%`` (NagVis writes it) matched neither the percent nor
    # the relative pattern and every such object stacked at the origin.
    assert _parse_coord("50%").ref is None
    assert _coord("50%") != 0


def test_coord_relative_starts_at_the_origin_until_resolved() -> None:
    # The offset is NOT the absolute value: an unresolvable reference (dangling or
    # cyclic) would otherwise place the object at x=-40, off the canvas.
    coord = _parse_coord("other%-40")
    assert (coord.ref, coord.offset, coord.value) == ("other", -40, 0)


def test_coord_invalid_returns_zero() -> None:
    assert _coord("invalid") == 0
    assert _coord("abc%def") == 0


def test_coord_multi_dash_does_not_raise() -> None:
    # A malformed coordinate must fall back to 0 rather than raise.
    assert _coord("--5") == 0
    assert _coord("---7") == 0


def test_line_coords_comma_separated() -> None:
    x, y, x2, y2, mid_x, mid_y = _line_coords({"x": "10,20", "y": "30,40"})
    assert (x.value, y.value, x2.value, y2.value) == (10, 30, 20, 40)
    assert mid_x is None and mid_y is None


def test_line_coords_separate_keys() -> None:
    x, y, x2, y2, mid_x, mid_y = _line_coords({"x": "10", "y": "30", "x2": "20", "y2": "40"})
    assert (x.value, y.value, x2.value, y2.value) == (10, 30, 20, 40)
    assert mid_x is None and mid_y is None


def test_line_coords_defaults_to_zero() -> None:
    x, y, x2, y2, mid_x, mid_y = _line_coords({})
    assert (x.value, y.value, x2.value, y2.value) == (0, 0, 0, 0)
    assert mid_x is None and mid_y is None


def test_line_coords_three_points_keeps_endpoints_and_bend() -> None:
    # NagVis two-segment line: first/last are endpoints, middle is the bend.
    x, y, x2, y2, mid_x, mid_y = _line_coords({"x": "100,300,500", "y": "50,200,90"})
    assert (x.value, y.value, x2.value, y2.value) == (100, 50, 500, 90)
    assert mid_x is not None and mid_y is not None
    assert (mid_x.value, mid_y.value) == (300, 200)


def test_cfg_to_map_defaults() -> None:
    parsed_map = cfg_to_map("", "mymap")
    assert parsed_map["name"] == "mymap"
    assert parsed_map["alias"] == "mymap"
    assert parsed_map["objects"] == []


def test_cfg_to_map_global_alias() -> None:
    content = "define global {\n    alias = My Map\n}\n"
    parsed_map = cfg_to_map(content, "mymap")
    assert parsed_map["alias"] == "My Map"


def test_cfg_to_map_global_map_image() -> None:
    content = "define global {\n    map_image = bg.png\n}\n"
    parsed_map = cfg_to_map(content, "x")
    assert parsed_map["background_image"] == "bg.png"


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("data centre.cfg", "data_centre"),
        ("a" * 150 + ".cfg", "a" * 100),  # the daemon caps the name at 100
        ("***.cfg", "___"),
        ("", "imported_map"),
    ],
)
def test_map_name_from_filename(filename: str, expected: str) -> None:
    assert map_name_from_filename(filename) == expected


def test_cfg_to_map_global_background_color() -> None:
    content = "define global {\n    background_color = #202020\n}\n"
    assert cfg_to_map(content, "x")["background_color"] == "#202020"


def test_cfg_to_map_global_background_color_invalid_falls_back() -> None:
    content = "define global {\n    background_color = rgb(1,2,3)\n}\n"
    assert cfg_to_map(content, "x")["background_color"] == "#ffffff"


def test_cfg_to_map_global_iconset() -> None:
    content = "define global {\n    iconset = std_big\n}\n"
    parsed_map = cfg_to_map(content, "x")
    assert parsed_map["icon_size"] == 30


def _first_obj(parsed_map: MapPayload) -> MapObject:
    return parsed_map["objects"][0]


def test_cfg_to_map_host() -> None:
    content = (
        "define host {\n"
        "    object_id = 1\n"
        "    host_name = server1\n"
        "    x = 100\n"
        "    y = 200\n"
        "    only_hard_states = 1\n"
        "    recognize_services = 1\n"
        "}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["id"] == "host_1"
    assert obj["type"] == "host"
    assert obj["host_name"] == "server1"
    assert obj["x"] == 100
    assert obj["y"] == 200
    assert obj["only_hard_states"] is True
    assert obj["recognize_services"] is True


def test_cfg_to_map_host_without_flags() -> None:
    content = "define host {\n    object_id = 2\n    host_name = s\n    x = 0\n    y = 0\n}\n"
    obj = _first_obj(cfg_to_map(content, "test"))
    assert "only_hard_states" not in obj
    assert "recognize_services" not in obj


def test_cfg_to_map_service() -> None:
    content = (
        "define service {\n"
        "    object_id = 3\n"
        "    host_name = server1\n"
        "    service_description = CPU Load\n"
        "    x = 50\n"
        "    y = 60\n"
        "}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["id"] == "service_3"
    assert obj["type"] == "service"
    assert obj["host_name"] == "server1"
    assert obj["service_description"] == "CPU Load"


def test_cfg_to_map_line_weathermap() -> None:
    # The legacy format encodes weathermap-style lines via line_type 13/14/15
    # on a stateful service block (view_type=line). Each variant decomposes
    # into shape (arrow_inward) + perfdata-label mode + weather-color flag.
    content = (
        "define service {\n"
        "    object_id = 4\n"
        "    x = 10,20\n"
        "    y = 30,40\n"
        "    line_type = 15\n"
        "    view_type = line\n"
        "    host_name = router1\n"
        "    service_description = Traffic\n"
        "}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["id"] == "line_4"
    assert obj["type"] == "line"
    assert obj["line_style"] == "arrow_inward"
    assert obj["line_perfdata_label"] == "bandwidth"
    assert obj["line_weather_color"] is True
    assert obj["host_name"] == "router1"
    assert obj["service_description"] == "Traffic"


def test_cfg_to_map_line_plain_no_host() -> None:
    # line_type=12 is the truly plain, no-arrow line.
    content = "define line {\n    x = 0,10\n    y = 0,10\n    line_type = 12\n}\n"
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["line_style"] == "plain"
    assert "host_name" not in obj


@pytest.mark.parametrize(
    "nagvis_width, expected",
    [
        ("0", 1),  # NagVis hairline; the daemon's minimum is 1
        ("3", 6),  # NagVis stores the half-width, Maps the full stroke
        ("10", 20),
        ("15", 20),  # would be 30 — the daemon's maximum is 20
    ],
)
def test_cfg_to_map_line_width_stays_within_the_daemons_range(
    nagvis_width: str, expected: int
) -> None:
    content = f"define line {{\n    x = 0,10\n    y = 0,10\n    line_width = {nagvis_width}\n}}\n"
    assert _first_obj(cfg_to_map(content, "test"))["line_width"] == expected


def test_cfg_to_map_line_color_border_invalid_falls_back() -> None:
    content = "define line {\n    x = 0,10\n    y = 0,10\n    line_color_border = rgb(1,2,3)\n}\n"
    assert _first_obj(cfg_to_map(content, "test"))["line_color_border"] == "#000000"


def test_cfg_to_map_line_default_type_is_arrow_end() -> None:
    # Default line_type is 11 (arrow_end) when omitted in the .cfg.
    content = "define line {\n    x = 0,10\n    y = 0,10\n}\n"
    assert _first_obj(cfg_to_map(content, "test"))["line_style"] == "arrow_end"


def test_cfg_to_map_line_bend_kept_as_mid() -> None:
    # A three-coordinate line keeps its endpoints and stores the bend as mid_*.
    content = "define line {\n    x = 100,300,500\n    y = 50,200,90\n    line_type = 13\n}\n"
    obj = _first_obj(cfg_to_map(content, "test"))
    assert (obj["x"], obj["y"], obj["x2"], obj["y2"]) == (100, 50, 500, 90)
    assert (obj["mid_x"], obj["mid_y"]) == (300, 200)


def test_cfg_to_map_line_two_points_has_no_mid() -> None:
    content = "define line {\n    x = 0,10\n    y = 0,10\n}\n"
    obj = _first_obj(cfg_to_map(content, "test"))
    assert "mid_x" not in obj and "mid_y" not in obj


def test_cfg_to_map_line_type_inherited_from_template() -> None:
    # NagVis lines often carry no explicit line_type — it comes from a
    # referenced template. Without resolving template > object these lines
    # silently fall back to the built-in default (11 = plain arrow).
    content = (
        "define template {\n    name = wm\n    line_type = 13\n}\n"
        "define line {\n    object_id = l1\n    x = 10,20\n    y = 30,40\n"
        "    template = wm\n}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["line_style"] == "arrow_inward"
    assert obj["line_perfdata_label"] == "percent"
    assert obj["line_weather_color"] is True
    assert "name" not in obj
    assert "template" not in obj


def test_cfg_to_map_element_line_type_overrides_template() -> None:
    content = (
        "define template {\n    name = wm\n    line_type = 13\n}\n"
        "define line {\n    object_id = l1\n    x = 10,20\n    y = 30,40\n"
        "    template = wm\n    line_type = 12\n}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["line_style"] == "plain"
    assert obj.get("line_weather_color") in (None, False)


def test_cfg_to_map_line_type_inherited_from_global() -> None:
    content = (
        "define global {\n    line_type = 13\n}\n"
        "define line {\n    object_id = l1\n    x = 10,20\n    y = 30,40\n}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["line_style"] == "arrow_inward"
    assert obj["line_weather_color"] is True


def test_cfg_to_map_global_backend_not_inherited_by_objects() -> None:
    # backend_id stays map-level: a global backend must not become a
    # per-object connection_id override.
    content = (
        "define global {\n    backend_id = primary\n    line_type = 13\n}\n"
        "define line {\n    object_id = l1\n    x = 10,20\n    y = 30,40\n}\n"
    )
    parsed_map = cfg_to_map(content, "test")
    assert parsed_map["connection_id"] == "primary"
    obj = _first_obj(parsed_map)
    assert "connection_id" not in obj
    assert obj["line_weather_color"] is True


def test_cfg_to_map_weathermap_metric_defaults_to_in_out() -> None:
    # NagVis weathermap lines need no metric config; in/out are matched against
    # the service perfdata by the implicit "in"/"out" labels.
    content = (
        "define service {\n    object_id = l1\n    x = 10,20\n    y = 30,40\n"
        "    view_type = line\n    line_type = 13\n"
        "    host_name = sw1\n    service_description = Interface WAN\n}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["line_weather_color"] is True
    assert obj["weathermap_metric"] == "in"
    assert obj["weathermap_metric_out"] == "out"


def test_cfg_to_map_weathermap_explicit_label_wins() -> None:
    content = (
        "define service {\n    object_id = l1\n    x = 10,20\n    y = 30,40\n"
        "    view_type = line\n    line_type = 13\n    line_label_in = if_in_octets\n"
        "    host_name = sw1\n    service_description = Interface WAN\n}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["weathermap_metric"] == "if_in_octets"
    assert obj["weathermap_metric_out"] == "out"


def test_cfg_to_map_plain_line_gets_no_weathermap_metric() -> None:
    content = (
        "define line {\n    object_id = l1\n    x = 10,20\n    y = 30,40\n    line_type = 11\n}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["line_style"] == "arrow_end"
    assert "weathermap_metric" not in obj
    assert "weathermap_metric_out" not in obj


def test_cfg_to_map_default_z_is_ten_and_objects_inherit() -> None:
    # NagVis' global default is z=10; objects without explicit z stay unset
    # so the renderer resolves them against the map's default_z.
    content = "define host {\n    object_id = 1\n    host_name = h\n    x = 5\n    y = 6\n}\n"
    parsed_map = cfg_to_map(content, "test")
    assert parsed_map["default_z"] == 10
    assert "z" not in _first_obj(parsed_map)


def test_cfg_to_map_explicit_z_is_kept() -> None:
    content = "define host {\n    object_id=1\n    host_name=h\n    x=5\n    y=6\n    z=42\n}\n"
    assert _first_obj(cfg_to_map(content, "test"))["z"] == 42


def test_cfg_to_map_shape() -> None:
    content = "define shape {\n    object_id = 5\n    x = 50\n    y = 60\n    icon = img.png\n}\n"
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["id"] == "image_5"
    assert obj["type"] == "image"
    assert obj["image_src"] == "img.png"


def test_cfg_to_map_textbox_coordinates() -> None:
    # nagvis_classic anchors top-left, so raw NagVis coords are preserved
    content = (
        "define textbox {\n"
        "    object_id = 6\n"
        "    x = 100\n"
        "    y = 200\n"
        "    w = 200\n"
        "    h = 40\n"
        "    text = Hello\n"
        "}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["x"] == 100
    assert obj["y"] == 200


def test_cfg_to_map_textbox_br_to_newline() -> None:
    content = "define textbox {\n    x = 0\n    y = 0\n    text = Hello<br>World\n}\n"
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["label"]["text"] == "Hello\nWorld"


def test_cfg_to_map_textbox_html_stripped() -> None:
    content = "define textbox {\n    x = 0\n    y = 0\n    text = <b>Bold</b> text\n}\n"
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["label"]["text"] == "Bold text"


def test_cfg_to_map_textbox_html_rgb_color_falls_back() -> None:
    content = (
        "define textbox {\n"
        "    x = 0\n"
        "    y = 0\n"
        '    text = <span style="color: rgb(255,0,0)">Alert</span>\n'
        "}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["label"]["color"] == "#000000"


def test_cfg_to_map_textbox_background_color_is_not_text_color() -> None:
    # `background-color:` must not be picked up as the `color:` text color.
    content = (
        "define textbox {\n    x = 0\n    y = 0\n"
        '    text = <span style="background-color:#222222">Hi</span>\n}\n'
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["label"]["color"] == "#000000"


def test_cfg_to_map_textbox_explicit_color_after_background() -> None:
    content = (
        "define textbox {\n    x = 0\n    y = 0\n"
        '    text = <span style="background-color:#222;color:#0f0">Hi</span>\n}\n'
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["label"]["color"] == "#0f0"


@pytest.mark.parametrize("target", ["main", "frames", "main_window"])
def test_cfg_to_map_url_target_frameset_targets(target: str) -> None:
    content = (
        f"define host {{\n    host_name = s\n    x = 0\n    y = 0\n    url_target = {target}\n}}\n"
    )
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["url_target"] == "_blank", f"Expected _blank for {target}"


def test_cfg_to_map_url_target_custom() -> None:
    content = "define host {\n    host_name = s\n    x = 0\n    y = 0\n    url_target = _self\n}\n"
    obj = _first_obj(cfg_to_map(content, "test"))
    assert obj["url_target"] == "_self"


def test_cfg_to_map_counter_id_without_object_id() -> None:
    content = (
        "define host {\n    host_name = s1\n    x = 0\n    y = 0\n}\n"
        "define host {\n    host_name = s2\n    x = 10\n    y = 10\n}\n"
    )
    parsed_map = cfg_to_map(content, "test")
    assert [obj["id"] for obj in parsed_map["objects"]] == ["host_1", "host_2"]


def test_cfg_to_map_unknown_block_skipped() -> None:
    content = (
        "define futuretype {\n    foo = bar\n}\n"
        "define host {\n    object_id = 99\n    host_name = s\n    x = 0\n    y = 0\n}\n"
    )
    parsed_map = cfg_to_map(content, "test")
    assert len(parsed_map["objects"]) == 1
    assert _first_obj(parsed_map)["host_name"] == "s"


def test_gadget_url_rawnumbers_maps_to_value() -> None:
    content = (
        "define global {\n    alias = Map\n}\n"
        "define service {\n    host_name = srv\n    service_description = CPU load\n"
        "    x = 10\n    y = 10\n    view_type = gadget\n    gadget_url = rawNumbers.php\n}\n"
    )
    obj = _first_obj(cfg_to_map(content, "m"))
    assert obj["display"] == {"mode": "gadget", "gadget_type": "value", "gadget_metric": None}


def test_view_type_gadget_without_url_defaults_to_gauge() -> None:
    # The legacy format defaults a gadget service without explicit gadget_url
    # to the speedometer; Maps follows suit so the icon doesn't silently
    # fall back to a plain icon.
    content = (
        "define service {\n"
        "    object_id = 9\n"
        "    host_name = h\n"
        "    service_description = CPU\n"
        "    x = 0\n"
        "    y = 0\n"
        "    view_type = gadget\n"
        "}\n"
    )
    obj = _first_obj(cfg_to_map(content, "x"))
    assert obj["display"] == {"mode": "gadget", "gadget_type": "gauge", "gadget_metric": None}


def test_worldmap_global_becomes_geo_view() -> None:
    text = (
        "define global {\n object_id=0\n sources=worldmap\n"
        " worldmap_center=50.868,10.217\n worldmap_zoom=6\n worldmap_tiles_saturate=33\n}\n"
    )
    parsed_map = cfg_to_map(text, "wm")
    assert parsed_map["view"] == {
        "type": "worldmap",
        "lat": 50.868,
        "lng": 10.217,
        "zoom": 6,
        "tile_saturate": 33.0,
    }
    # Markers live in a sidecar file the text-only import can't read.
    assert parsed_map["objects"] == []


def test_automap_layer_depths_stay_within_the_daemons_range() -> None:
    content = (
        "define global {\n    sources = automap\n    child_layers = 50\n    parent_layers = -3\n}\n"
    )
    view = cfg_to_map(content, "am")["view"]
    assert view["type"] == "flow"
    assert (view["child_layers"], view["parent_layers"]) == (20, -1)


def test_automap_unparseable_layer_depth_is_left_to_the_daemon_default() -> None:
    # -1 means "unlimited" to the daemon — too expensive to inherit from a typo.
    content = "define global {\n    sources = automap\n    child_layers = abc\n}\n"
    view = cfg_to_map(content, "am")["view"]
    assert view["type"] == "flow"
    assert "child_layers" not in view


def test_relative_coordinate_resolves_against_the_explicit_object_id() -> None:
    content = (
        "define host {\n    object_id = anchor\n    host_name = h1\n    x = 100\n    y = 50\n}\n"
        "define host {\n    host_name = h2\n    x = anchor%+40\n    y = anchor%-10\n}\n"
    )
    objects = cfg_to_map(content, "m")["objects"]
    assert (objects[1]["x"], objects[1]["y"]) == (140, 40)


def test_counter_derived_ids_are_not_referenceable() -> None:
    # Only an explicit object_id is indexed for reference resolution. The second
    # block gets the counter id "2"; a reference to it must NOT resolve to it (it
    # used to, because the index was derived from the generated object id).
    content = (
        "define host {\n    object_id = anchor\n    host_name = h1\n    x = 100\n    y = 100\n}\n"
        "define host {\n    host_name = h2\n    x = 700\n    y = 700\n}\n"
        "define host {\n    host_name = h3\n    x = two%+5\n    y = two%+5\n}\n"
    )
    objects = cfg_to_map(content, "m")["objects"]
    assert objects[1]["id"] == "host_2", "the second block is counter-derived"
    # Unresolvable reference: the object stays at the origin (visible, reachable)
    # instead of inheriting a foreign position.
    assert (objects[2]["x"], objects[2]["y"]) == (0, 0)


def test_object_count_is_capped() -> None:
    # The byte cap alone does not bound the response: tiny define blocks expand
    # into full map objects.
    content = "define host {\n    host_name = h\n}\n" * (_cfg_import._MAX_CFG_OBJECTS + 1)  # noqa: SLF001
    with pytest.raises(MKUserError):
        cfg_to_map(content, "big")


def test_geomap_global_becomes_geo_view() -> None:
    parsed_map = cfg_to_map("define global {\n sources=geomap\n geomap_zoom=7\n}\n", "gm")
    view = parsed_map["view"]
    assert view["type"] == "worldmap"
    assert view["zoom"] == 7


def test_dynmap_is_not_converted_to_geo() -> None:
    parsed_map = cfg_to_map("define global {\n sources=dynmap\n}\n", "dm")
    assert parsed_map["view"]["type"] == "static"


def test_container_imports_as_graph_iframe() -> None:
    text = (
        "define container {\n object_id=c1\n x=100\n y=50\n"
        " url=http://example.com/dash\n w=300\n h=200\n}\n"
    )
    obj = _first_obj(cfg_to_map(text, "c"))
    assert obj["type"] == "graph"
    assert obj["graph_embed_type"] == "iframe"
    assert obj["graph_width"] == 300 and obj["graph_height"] == 200


# An inlined NagVis .cfg exercising every block type and view_type variant the
# parser supports. This pins the expected import shape so future parser changes
# can't silently regress (e.g. dropping aggregations or misclassifying a
# service-as-line as an icon).
def _by_id(parsed_map: MapPayload, obj_id: str) -> MapObject:
    matches = [o for o in parsed_map["objects"] if o["id"] == obj_id]
    assert len(matches) == 1, f"expected exactly one object with id {obj_id!r}, got {len(matches)}"
    return matches[0]


def test_fixture_global_settings(all_objects_map: MapPayload) -> None:
    assert all_objects_map["alias"] == "All Objects"
    assert all_objects_map["connection_id"] == "ZWEIFUENF"
    assert all_objects_map["icon_size"] == 30  # iconset=std_big
    assert all_objects_map["view"] == {"type": "static"}
    # cfg-import maps opt into the NagVis-classic renderer with a white canvas
    assert all_objects_map["render_mode"] == "nagvis_classic"
    assert all_objects_map["background_color"] == "#ffffff"


def test_fixture_object_count(all_objects_map: MapPayload) -> None:
    # 1 host + 4 services (icon/gadget/line-via-view_type/url) + 1 hg + 1 sg + 4 lines
    # (3 stateless: arrow_inward/arrow_end/plain + 1 service-bound weathermap) +
    # 1 textbox + 1 image (shape) + 1 map link + 1 aggregation = 15 objects.
    assert len(all_objects_map["objects"]) == 15


def test_fixture_host(all_objects_map: MapPayload) -> None:
    o = _by_id(all_objects_map, "host_h00001")
    assert o["type"] == "host"
    assert o["host_name"] == "localhost"
    assert (o["x"], o["y"]) == (200, 120)
    assert o["only_hard_states"] is True
    assert o["recognize_services"] is True


def test_fixture_service_icon(all_objects_map: MapPayload) -> None:
    o = _by_id(all_objects_map, "service_s00001")
    assert o["type"] == "service"
    assert o["service_description"] == "Memory"
    assert o["display"] == {"mode": "icon"}
    assert o["only_hard_states"] is True


def test_fixture_service_gadget(all_objects_map: MapPayload) -> None:
    o = _by_id(all_objects_map, "service_s00002")
    # gadget_url=std_speedometer.php must map to Maps gadget_type=gauge
    # (otherwise the gauge renders empty because no metric is selected).
    assert o["display"] == {"mode": "gadget", "gadget_type": "gauge", "gadget_metric": None}


def test_fixture_service_with_view_type_line_becomes_line(
    all_objects_map: MapPayload,
) -> None:
    # The legacy format encodes lines as service blocks with view_type=line.
    o = _by_id(all_objects_map, "line_s00003")
    assert o["type"] == "line"
    assert (o["x"], o["y"], o["x2"], o["y2"]) == (200, 320, 800, 320)
    assert o["host_name"] == "localhost"
    assert o["service_description"] == "Interface 2"
    # No explicit line_type → default (11 → arrow_end)
    assert o["line_style"] == "arrow_end"


def test_fixture_hostgroup(all_objects_map: MapPayload) -> None:
    o = _by_id(all_objects_map, "hostgroup_hg0001")
    assert o["type"] == "hostgroup"
    assert o["group_name"] == "linux-servers"


def test_fixture_servicegroup(all_objects_map: MapPayload) -> None:
    o = _by_id(all_objects_map, "servicegroup_sg0001")
    assert o["type"] == "servicegroup"
    assert o["group_name"] == "disk-services"


@pytest.mark.parametrize(
    ("obj_id", "expected_style"),
    [
        pytest.param("line_l00001", "arrow_inward", id="type-10-bidirectional"),
        pytest.param("line_l00002", "arrow_end", id="type-11"),
        pytest.param("line_l00003", "plain", id="type-12"),
    ],
)
def test_fixture_line_styles(all_objects_map: MapPayload, obj_id: str, expected_style: str) -> None:
    o = _by_id(all_objects_map, obj_id)
    assert o["type"] == "line"
    assert o["line_style"] == expected_style


def test_fixture_service_bound_weathermap_line_carries_metrics(
    all_objects_map: MapPayload,
) -> None:
    # A bandwidth-labelled weathermap line decomposes into arrow_inward shape +
    # perfdata_label='bandwidth' + weather_color=True with both metrics resolved.
    o = _by_id(all_objects_map, "line_l00004")
    assert o["type"] == "line"
    assert o["line_style"] == "arrow_inward"
    assert o["line_perfdata_label"] == "bandwidth"
    assert o["line_weather_color"] is True
    assert o["host_name"] == "localhost"
    assert o["service_description"] == "Interface 2"
    assert o["weathermap_metric"] == "in"
    assert o["weathermap_metric_out"] == "out"
    # cfg's line_width=5 is NagVis half-width; doubled on import.
    assert o["line_width"] == 10


def test_fixture_textbox_html_stripped(all_objects_map: MapPayload) -> None:
    o = _by_id(all_objects_map, "textbox_tb0001")
    assert o["type"] == "textbox"
    # <b>…</b> and other tags stripped, <br> → \n, &nbsp; → real space
    assert o["label"]["text"] == "Hello World\nsecond line"
    # nagvis_classic anchors top-left, so x/y are the raw NagVis coords
    assert (o["x"], o["y"]) == (200, 820)


def test_fixture_shape_imports_as_image(all_objects_map: MapPayload) -> None:
    o = _by_id(all_objects_map, "image_sh0001")
    assert o["type"] == "image"
    assert o["image_src"] == "std_nagvis.png"


def test_fixture_map_link(all_objects_map: MapPayload) -> None:
    o = _by_id(all_objects_map, "map_m00001")
    assert o["type"] == "map"
    assert o["map_name"] == "other-map"


def test_fixture_aggregation(all_objects_map: MapPayload) -> None:
    # `define aggr { name=… }` must import as type=aggregation, not be dropped.
    o = _by_id(all_objects_map, "aggregation_ag0001")
    assert o["type"] == "aggregation"
    assert o["aggregation_id"] == "Host localhost"


def test_fixture_url_target_frameset_rewritten_to_blank(
    all_objects_map: MapPayload,
) -> None:
    o = _by_id(all_objects_map, "service_s00004")
    assert o["url"] == "https://example.com/dashboard"
    # url_target=main is a legacy frameset target → rewritten to _blank
    assert o["url_target"] == "_blank"


def test_cfg_to_map_out_of_range_values_still_validate() -> None:
    """A .cfg carrying values the daemon rejects must not cost the whole map.

    The daemon validates the map as one document, so a single out-of-range
    number or unsupported color used to 422 the import and leave every object
    without live state — not just the offending one.
    """
    objects_cfg = (
        "define global {\n"
        "    background_color = rgb(1,2,3)\n"
        "}\n"
        "define line {\n"
        "    x = 0,10\n"
        "    y = 0,10\n"
        "    line_width = 99\n"
        "    line_color_border = expression(alert(1))\n"
        "}\n"
        "define textbox {\n"
        "    x = 0\n"
        "    y = 0\n"
        '    text = <span style="color: rgb(255,0,0)">Alert</span>\n'
        "    border_color = rgb(9,9,9)\n"
        "}\n"
    )
    parsed_map = cfg_to_map(objects_cfg, map_name_from_filename("x" * 150 + ".cfg"))
    assert len(parsed_map["objects"]) == 2
    DaemonMapConfig.model_validate(parsed_map)

    # An automap has no objects of its own; its layer depths are the risk.
    automap_cfg = (
        "define global {\n    sources = automap\n    child_layers = 50\n    parent_layers = -3\n}\n"
    )
    DaemonMapConfig.model_validate(cfg_to_map(automap_cfg, "am"))


# ---------------------------------------------------------------------------
# Per-object monitoring connection (NagVis ``backend_id`` per object)
# ---------------------------------------------------------------------------


def test_cfg_to_map_object_backend_becomes_a_connection_override() -> None:
    # NagVis allows one map to mix monitoring sources; the daemon groups its
    # state fetch by connection, so the override has to survive the import.
    content = (
        "define global {\n    backend_id = primary\n}\n"
        "define host {\n    host_name = h1\n    backend_id = other_site\n"
        "    x = 10\n    y = 20\n    object_id = o1\n}\n"
    )
    assert _first_obj(cfg_to_map(content, "test"))["connection_id"] == "other_site"


def test_cfg_to_map_object_backend_inherited_from_its_template() -> None:
    content = (
        "define template {\n    name = t1\n    backend_id = other_site\n}\n"
        "define host {\n    host_name = h1\n    template = t1\n"
        "    x = 10\n    y = 20\n    object_id = o1\n}\n"
    )
    assert _first_obj(cfg_to_map(content, "test"))["connection_id"] == "other_site"


def test_resolve_keeps_an_object_override_that_names_a_configured_connection() -> None:
    map_cfg = cfg_to_map(
        "define global {\n    backend_id = primary\n}\n"
        "define host {\n    host_name = h1\n    backend_id = secondary\n"
        "    x = 10\n    y = 20\n    object_id = o1\n}\n",
        "test",
    )

    assert resolve_connection_ids(map_cfg, ["primary", "secondary"]) == []

    assert map_cfg["connection_id"] == "primary"
    assert _first_obj(map_cfg)["connection_id"] == "secondary"


def test_resolve_drops_an_object_override_equal_to_the_maps_connection() -> None:
    # Redundant: the object would resolve against the map's connection anyway.
    map_cfg = cfg_to_map(
        "define global {\n    backend_id = primary\n}\n"
        "define host {\n    host_name = h1\n    backend_id = primary\n"
        "    x = 10\n    y = 20\n    object_id = o1\n}\n",
        "test",
    )

    assert resolve_connection_ids(map_cfg, ["primary"]) == []

    assert "connection_id" not in _first_obj(map_cfg)


def test_resolve_drops_an_unconfigured_object_override_and_says_so() -> None:
    """An unknown connection must not be silently swapped for a different one.

    Pointing the object at another connection would resolve it against a
    same-named host on the wrong site and report that host's state as if it were
    the right one — so the override is dropped and the operator told.
    """
    map_cfg = cfg_to_map(
        "define global {\n    backend_id = primary\n}\n"
        "define host {\n    host_name = h1\n    backend_id = gone\n"
        "    x = 10\n    y = 20\n    object_id = o1\n}\n"
        "define host {\n    host_name = h2\n    backend_id = gone\n"
        "    x = 30\n    y = 40\n    object_id = o2\n}\n",
        "test",
    )

    warnings = resolve_connection_ids(map_cfg, ["primary"])

    assert all("connection_id" not in obj for obj in map_cfg["objects"])
    assert len(warnings) == 1
    assert "'gone'" in warnings[0]
    assert "2 objects" in warnings[0]


def test_resolve_reports_the_map_level_fallback() -> None:
    map_cfg = cfg_to_map("define global {\n    backend_id = gone\n}\n", "test")

    warnings = resolve_connection_ids(map_cfg, ["primary"])

    assert map_cfg["connection_id"] == "primary"
    assert len(warnings) == 1
    assert "'gone'" in warnings[0] and "'primary'" in warnings[0]


def test_resolve_follows_the_map_when_object_and_map_share_a_gone_backend() -> None:
    # Both named the same source installation's backend: the map is remapped and
    # the object simply follows it, so this is not worth a second warning.
    map_cfg = cfg_to_map(
        "define global {\n    backend_id = gone\n}\n"
        "define host {\n    host_name = h1\n    backend_id = gone\n"
        "    x = 10\n    y = 20\n    object_id = o1\n}\n",
        "test",
    )

    warnings = resolve_connection_ids(map_cfg, ["primary"])

    assert map_cfg["connection_id"] == "primary"
    assert "connection_id" not in _first_obj(map_cfg)
    assert len(warnings) == 1  # only the map-level fallback
