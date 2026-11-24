#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Parse legacy NagVis ``.cfg`` map content into a Checkmk Maps map dict.

This is stateless format knowledge (pure text → dict), so it lives GUI-side with
the rest of map authoring — the daemon owns only live state, not import.
:func:`parse_cfg_upload` below wraps the parser for the SPA's import flow; the
endpoint serving it is in :mod:`cmk.maps.rest_api.internal.cfg_import`.
"""

import codecs
import contextlib
import hashlib
import html
import re
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, get_args, Literal, TypedDict

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _, ungettext
from cmk.maps.gui._filter_check import check_object_filter
from cmk.maps.gui._settings import connection_choices, map_object_defaults
from cmk.maps.shared.filters import (
    bound_type_of,
    check_host_member_patterns,
    MEMBER_PATTERN_MAX_LENGTH,
    normalize_object_filter,
    validate_member_pattern,
)
from cmk.maps.shared.geo import bounded_view, parse_degrees
from cmk.maps.shared.map_compat import unique_ids
from cmk.maps.shared.map_name import MAP_NAME_MAX_LENGTH
from cmk.maps.shared.map_payload import (
    FlowView,
    GadgetType,
    GeoView,
    GRID_FIELD_DEFAULTS,
    GRID_OFFSET_MAX,
    GRID_PER_ROW_MAX,
    GridObjectType,
    LABEL_FIELD_DEFAULTS,
    LabelAlign,
    LabelWeight,
    LinePerfdataLabel,
    LineStyle,
    MAP_FIELD_DEFAULTS,
    MapDisplay,
    MapLabel,
    MapObject,
    MapPayload,
    MonitoredObjectType,
)
from cmk.maps.shared.validators import coerce_color, coerce_graph_url, coerce_user_url

# A NagVis .cfg is a small text file; cap the upload before the whole-file regex
# scan + multi-pass reference resolver run over it, mirroring the icon/background
# upload caps. Real exported maps are well under this.
MAX_CFG_BYTES = 5 * 1024 * 1024  # 5 MB

# The byte cap alone does not bound the result: one ~25-byte `define` block
# becomes a full map object in the JSON response, so a 5 MB file of tiny blocks
# would balloon the draft the SPA has to hold. Real exported maps stay well below
# this; an automap this large is unusable as a map anyway.
_MAX_CFG_OBJECTS = 2000

# Each block that uses a template holds a copy of the template's parameters, so a
# chain of templates or one large template used by many objects would multiply
# the file far beyond the byte cap.
_MAX_INHERITED_PARAMS = 100 * _MAX_CFG_OBJECTS

# What templates and the global block pass on is copied into each object, so a
# large value they hold is multiplied by the objects using it.
_MAX_OBJECT_SETTINGS_CHARS = 4 * MAX_CFG_BYTES


# Legacy line_type integers from the .cfg map format; 20 is not a valid value.
_LINE_STYLES: dict[int, LineStyle] = {
    10: "arrow_inward",  # -------><------- bidirectional
    11: "arrow_end",  # --------------->
    12: "plain",  # ---------------- no arrows
    13: "arrow_inward",  # ---%---><---%---
    14: "arrow_inward",  # --%+BW-><-%+BW--
    15: "arrow_inward",  # ---BW--><--BW---
}
_DEFAULT_LINE_STYLE: LineStyle = _LINE_STYLES[11]

# 13/14/15 are the only ones that carry perfdata labels, always with the weather
# gradient. The perfdata is a service's, so only a line showing one keeps them.
_LINE_PERFDATA_LABELS: dict[int, LinePerfdataLabel] = {
    13: "percent",
    14: "both",
    15: "bandwidth",
}

# The pixel size of the iconsets NagVis ships.
ICONSET_SIZE: dict[str, int] = {
    "std_big": 32,
    "std_medium": 22,
    "std": 22,
    "std_small": 16,
}
# The icon sets NagVis ships; those not in ICONSET_SIZE take the map's icon size.
_STOCK_ICONSETS = frozenset({*ICONSET_SIZE, "std_area", "std_dot", "std_geo"})

_FRAMESET_TARGETS = {"main", "frames", "main_window"}

# Stock legacy gadget URL → Maps gadget_type. Custom/unknown gadget_urls
# fall back to icon mode with a warning — there is no equivalent Maps renderer.
_GADGET_URL_MAP: dict[str, GadgetType] = {
    "std_speedometer.php": "gauge",
    "std_speedometer2.php": "gauge",
    "std_bar.php": "bar",
    "std_html_bar.php": "bar",
    "rawNumbers.php": "value",
}

# How large NagVis draws its stock gadgets at gadget_scale 100, width and height.
_NAGVIS_GADGET_SIZES: dict[str, tuple[int, int]] = {
    "std_speedometer.php": (220, 110),
    "std_speedometer2.php": (220, 110),
    "std_bar.php": (400, 50),
    "std_html_bar.php": (100, 30),
}
# NagVis draws them at one size whatever the gadget_scale.
_UNSCALED_GADGETS = frozenset({"std_speedometer.php", "std_html_bar.php"})
# Ten times NagVis' size; a larger one would only make the canvas huge.
_GADGET_SCALE_MAX = 1000
# The share of a bar gadget's size Maps draws its track at (GadgetRenderer.vue).
_BAR_TRACK_SHARE = 0.22
# How high Maps draws a gadget with a one-line caption (GadgetRenderer.vue): a bar
# as a share of its size, a gauge as a share plus the caption at the small font.
_BAR_HEIGHT_SHARE = 0.43
_GAUGE_HEIGHT_SHARE = 0.65
_GAUGE_CAPTION_HEIGHT = 12


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


_DEFINE_RE = re.compile(r"define\s+(\w+)\s*\{")
_PROPERTY_RE = re.compile(r"(\w+)\s*=\s*(.*)")


def _merge_templates(blocks: list[tuple[str, dict[str, str]]]) -> list[dict[str, str]]:
    """Each block's parameters with the template ``use`` names merged in, as NagVis does.

    In file order, a block takes the last template it names that exists, as
    merged so far; a template is found by the first one of its name.
    """
    first: dict[str, int] = {}
    for i, (block_type, p) in enumerate(blocks):
        if block_type == "template" and (name := p.get("name")):
            first.setdefault(name, i)
    merged = [p for _block_type, p in blocks]
    inherited = 0
    for i, (block_type, p) in enumerate(blocks):
        if block_type == "global":
            continue
        if used := [name for name in p.get("use", "").split(",") if name in first]:
            template = merged[first[used[-1]]]
            passed_on = {k: v for k, v in template.items() if k not in _NON_INHERITED_KEYS}
            inherited += len(passed_on)
            if inherited > _MAX_INHERITED_PARAMS:
                raise MKUserError(
                    "file",
                    _("The templates of the map pass on more than %(limit)d parameters.")
                    % {"limit": _MAX_INHERITED_PARAMS},
                )
            merged[i] = passed_on | p
    return merged


def _parse_blocks(text: str) -> list[tuple[str, dict[str, str]]]:
    """Read the blocks line by line, as NagVis does.

    Only a line starting with ``}`` ends a block, so a ``}`` inside a value (CSS in a
    textbox, say) stays part of that value. A ``define`` starts a new block even
    if the previous one was never closed, which NagVis then drops.
    """
    blocks: list[tuple[str, dict[str, str]]] = []
    current: tuple[str, dict[str, str]] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if m := _DEFINE_RE.match(line):
            current = (m.group(1).lower(), {})
        elif current is None:
            continue
        elif line.startswith("}"):
            blocks.append(current)
            current = None
        elif kv := _PROPERTY_RE.match(line):
            current[1][kv.group(1)] = kv.group(2).strip()
    return blocks


def _int(v: str | None, default: int = 0) -> int:
    try:
        return int(v) if v is not None else default
    except ValueError:
        return default


def _opt_int(v: str | None) -> int | None:
    """The integer *v* holds, or ``None`` when it is absent or not a number."""
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _bool(v: str | None, default: bool = False) -> bool:
    return (v or "").strip().lower() in ("1", "true", "yes") if v is not None else default


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _color(value: object, default: str) -> str:
    """A NagVis color, or *default* if the daemon would reject it.

    The daemon validates the map as one document, so a single unsupported value
    — a legacy ``rgb(...)`` out of a textbox's inline HTML, say — would cost the
    whole imported map its live state, not just that one object.
    """
    text = value.strip() if isinstance(value, str) else ""
    coerced = coerce_color(text or default)
    return coerced if isinstance(coerced, str) and coerced else default


_REL_COORD_RE = re.compile(r"^([A-Za-z0-9_]+)%([+-]?\d+)?$")
_PERCENT_COORD_RE = re.compile(r"^([+-]?\d+)%([+-]?\d+)?$")

# NagVis sizes a percent coordinate against the map's background image, which the
# text-only import cannot measure. Resolve it against the same nominal canvas the
# SPA uses for a map without a background (1920x1080) so percent-placed objects
# keep their relative layout instead of all collapsing onto the origin.
_PERCENT_CANVAS: Mapping[Literal["x", "y"], int] = {"x": 1920, "y": 1080}


class _Coord:
    """NagVis coordinate. ``ref`` is the referenced object_id if relative."""

    __slots__ = ("offset", "ref", "value")

    def __init__(self, value: int, ref: str | None = None, offset: int | None = None):
        self.value = value
        self.ref = ref
        self.offset = offset


def _parse_coord(v: str, axis: Literal["x", "y"] = "x") -> _Coord:
    v = v.strip()
    try:
        return _Coord(int(v))
    except ValueError:
        pass
    # Percent-of-canvas, with an optional pixel offset ("50%" or "50%100").
    if m := _PERCENT_COORD_RE.match(v):
        percent, offset = int(m.group(1)), _int(m.group(2))
        return _Coord(round(_PERCENT_CANVAS[axis] * percent / 100) + offset)
    if m := _REL_COORD_RE.match(v):
        # Relative to another object: the absolute value is only known once the
        # target resolves, so start at the origin rather than at the bare offset
        # — an unresolvable reference (dangling/cyclic) would otherwise place the
        # object at e.g. x=-40, off the canvas and out of the operator's reach.
        return _Coord(value=0, ref=m.group(1), offset=_int(m.group(2)))
    return _Coord(0)


_Axis = Literal["x", "y", "x2", "y2", "mid_x", "mid_y"]


@dataclass(frozen=True)
class _PendingRef:
    """A coordinate given relative to another object (NagVis ``other%+10``)."""

    ref: str
    offset: int


_Dropped = Literal["custom_gadget", "custom_iconset", "html_textbox", "line_cut"]


@dataclass
class _ImportObject:
    """One object under construction.

    Unresolved relative coordinates are held next to the payload rather than
    inside it, so the payload never carries importer bookkeeping that would have
    to be stripped again before it reaches the daemon.

    ``ref_id`` is the cfg's explicit ``object_id`` — the only thing another
    object's relative coordinate can name — and stays ``None`` for a block
    without one.
    """

    payload: MapObject
    pending: dict[_Axis, _PendingRef] = field(default_factory=dict)
    ref_id: str | None = None
    # A label's map coordinate on an axis whose object position is only known
    # once ``pending`` resolves.
    label_at: dict[Literal["x", "y"], int] = field(default_factory=dict)
    # What of the block Maps does not carry over, with the name it is known by
    # where the warning names one (the icon set).
    dropped: dict[_Dropped, str] = field(default_factory=dict)


def _pending(coords: Mapping[_Axis, _Coord]) -> dict[_Axis, _PendingRef]:
    return {
        axis: _PendingRef(c.ref, c.offset or 0) for axis, c in coords.items() if c.ref is not None
    }


def _set_explicit_z(payload: MapObject, p: dict[str, str]) -> None:
    """Write ``z`` only when the cfg block set it explicitly.

    NagVis stores no z on objects that use its global default (10); leaving z
    unset lets such objects inherit the map's ``default_z`` instead of each
    type inventing its own layer — reproducing NagVis layering 1:1.
    """
    if "z" in p:
        payload["z"] = _int(p["z"])


def _resolve_pending_refs(objects: list[_ImportObject]) -> None:
    """Resolve relative coordinates against the NagVis ``object_id`` index.

    Only blocks that carry an explicit ``object_id`` are indexed: a reference can
    name nothing else, and indexing the counter-derived ids too would let a block
    whose ``object_id`` happens to be a number shadow the n-th block. First
    definition wins if a cfg repeats an id.

    Iterates up to 5 passes so transitive chains (A → B → C) settle; NagVis
    itself warns about cycles so deeper chains are unexpected.
    """
    by_raw: dict[str, _ImportObject] = {}
    for obj in objects:
        if obj.ref_id:
            by_raw.setdefault(obj.ref_id, obj)
    for _attempt in range(5):
        changed = False
        for obj in objects:
            if not obj.pending:
                continue
            for axis, ref in list(obj.pending.items()):
                target = by_raw.get(ref.ref)
                if target is None:
                    continue
                # x2/y2/mid_x reuse the target's x/y — NagVis only stores one
                # endpoint per object, lines reuse it by axis-name match.
                base_axis: Literal["x", "y"] = "x" if axis in ("x", "x2", "mid_x") else "y"
                if base_axis in target.pending:
                    continue
                obj.payload[axis] = target.payload[base_axis] + ref.offset
                del obj.pending[axis]
                changed = True
        if not changed:
            break
    for obj in objects:
        for label_axis, at in obj.label_at.items():
            obj.payload["label"][label_axis] = at - obj.payload[label_axis]


def _axis_coords(
    raw: str, fallback_second: str, axis: Literal["x", "y"]
) -> tuple[_Coord, _Coord, _Coord | None]:
    """Parse one axis of a line into (start, end, optional bend).

    NagVis encodes a line's coords as a comma-separated list per axis. With
    three values (a two-segment line) the middle is the bend/meeting point;
    first and last are always the endpoints. Falls back to a separate
    ``x2``/``y2`` key when no comma is present.
    """
    if "," in raw:
        parts = [s.strip() for s in raw.split(",")]
        mid = _parse_coord(parts[1], axis) if len(parts) >= 3 else None
        return _parse_coord(parts[0], axis), _parse_coord(parts[-1], axis), mid
    return _parse_coord(raw, axis), _parse_coord(fallback_second, axis), None


def _line_coords(
    p: dict[str, str],
) -> tuple[_Coord, _Coord, _Coord, _Coord, _Coord | None, _Coord | None]:
    x, x2, mid_x = _axis_coords(p.get("x", "0"), p.get("x2", "0"), "x")
    y, y2, mid_y = _axis_coords(p.get("y", "0"), p.get("y2", "0"), "y")
    return x, y, x2, y2, mid_x, mid_y


def _label_map_coord(raw: str | None) -> int | None:
    """``label_x`` or ``label_y`` as a map coordinate; ``None`` for a keyword or a
    number relative to the object, a signed one or 0."""
    v = (raw or "").strip()
    try:
        at = int(v)
    except ValueError:
        return None
    return None if v[0] in "+-" or at == 0 else at


def _label_x(raw: str | None, object_x: int) -> int | None:
    """Where ``label_x`` puts the label's left edge, relative to the object.

    ``None`` for ``center``, NagVis' default, which centers the label on the
    icon instead. A signed number or 0 is relative to the object, any other
    number a map coordinate.
    """
    v = (raw or "center").strip().lower()
    if (at := _label_map_coord(v)) is not None:
        return at - object_x
    try:
        return int(v)
    except ValueError:
        return None


# CSS named colors are valid label backgrounds (see shared.validators), and the
# dark ones need light label text just like a dark hex value does. Only the names
# that actually decide the text color are listed — anything lighter than the
# threshold ends up on the same branch as an unknown name (dark text).
_DARK_NAMED_COLORS = frozenset(
    {
        "black",
        "brown",
        "darkblue",
        "darkgreen",
        "darkmagenta",
        "darkolivegreen",
        "darkred",
        "darkslateblue",
        "darkslategray",
        "darkslategrey",
        "dimgray",
        "dimgrey",
        "green",
        "indigo",
        "maroon",
        "midnightblue",
        "navy",
        "olive",
        "purple",
        "saddlebrown",
        "sienna",
        "teal",
    }
)


def _bg_brightness(value: str | None) -> float | None:
    if not value:
        return None
    v = value.strip().lower()
    if v in {"transparent", ""}:
        return None
    if v.startswith("#") and len(v) in (4, 7):
        try:
            if len(v) == 4:
                r, g, b = (int(c * 2, 16) for c in v[1:])
            else:
                r, g, b = int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16)
        except ValueError:
            return None
        return (r + g + b) / 3
    return None


def _bg_is_opaque_dark(value: str | None) -> bool:
    if (value or "").strip().lower() in _DARK_NAMED_COLORS:
        return True
    b = _bg_brightness(value)
    return b is not None and b < 100


def _label_y(raw: str | None, object_y: int, icon_size: int) -> int:
    """Where ``label_y`` puts the label's top edge, relative to the object.

    NagVis defaults to ``bottom``, which puts the label right below the icon.
    A signed number or 0 is relative to the object, any other number a map
    coordinate.
    """
    if raw is None:
        return icon_size
    v = raw.strip().lower()
    if v in ("", "bottom"):
        return icon_size
    if (at := _label_map_coord(v)) is not None:
        return at - object_y
    try:
        return int(v)
    except ValueError:
        return icon_size


def _hidden_label() -> MapLabel:
    """A complete but hidden ``LabelConfig`` for objects that carry no label.

    Lines, shapes and containers render no label, but the map schema's
    ``LabelConfig`` requires all of ``show``/``x``/``y``/``size``/``color``/
    ``background`` — a bare ``{"show": False}`` is rejected on save. Emit a full,
    hidden config so the import round-trips through the Maps REST API.
    """
    return {**LABEL_FIELD_DEFAULTS, "show": False}


def _text_color_on(raw_bg: str | None) -> str:
    # Text NagVis draws in its black stays black on a light background of the
    # object's own; on Maps' own surface it takes the Maps color.
    if _color(raw_bg, "transparent") != "transparent" and not _bg_is_opaque_dark(raw_bg):
        return "#000000"
    return LABEL_FIELD_DEFAULTS["color"]


def _label(
    p: dict[str, str], object_x: int, object_y: int, icon_size: int, *, show_default: bool = True
) -> MapLabel:
    raw_bg = p.get("label_background", "transparent")
    background = _color(raw_bg, "transparent")
    left = _label_x(p.get("label_x"), object_x)
    label: MapLabel = {
        "show": _bool(p.get("label_show"), show_default),
        "text": p.get("label_text") or None,
        "x": left or 0,
        "y": _label_y(p.get("label_y"), object_y, icon_size),
        "size": _int(p.get("label_size"), 11),
        "color": _color(p.get("label_color"), _text_color_on(raw_bg)),
        "background": background,
        "width": _int(p.get("label_width")) or None,
    }
    if left is not None:
        label["align"] = "left"
    return label


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------


# Only ``aggr`` is renamed; every other block type carries over verbatim.
_MONITOR_OBJECT_TYPES: dict[str, MonitoredObjectType] = {
    "host": "host",
    "service": "service",
    "hostgroup": "hostgroup",
    "servicegroup": "servicegroup",
    "dyngroup": "dyngroup",
    "map": "map",
    "aggr": "aggregation",
}

_BLOCK_TYPES = frozenset(_MONITOR_OBJECT_TYPES) | {"shape", "line", "textbox", "container"}

# Keys identifying a block — never inherited from a template/global layer.
_NON_INHERITED_KEYS = frozenset({"object_id", "name", "use"})

# Global-block keys that configure the map itself (handled by _apply_global)
# and must not be pushed onto every object as a default. backend_id stays
# map-level so an object only gets a connection override where its own block (or
# its template) names one — see the object loop in convert_cfg.
# view_type is excluded too: a global view_type=line would reroute every host
# into the line handler — view_type is inherited from templates (line/gadget
# templates), never from global.
_GLOBAL_MAP_KEYS = frozenset(
    {
        "alias",
        "map_image",
        "background_color",
        "backend_id",
        "connection_id",
        "iconset",
        "sources",
        "root",
        "child_layers",
        "parent_layers",
        "view_type",
        "filter_group",
        "dynmap_object_types",
        "dynmap_object_filter",
        "dynmap_init_x",
        "dynmap_init_y",
        "dynmap_offset_x",
        "dynmap_offset_y",
        "dynmap_per_row",
        "dynmap_sort",
        "dynmap_order",
    }
)


# NagVis geographic map sources that become a Maps geo map.
# ``dynmap`` is excluded — it is a dynamic-filter map, not geographic.
_GEO_SOURCES = {"worldmap", "geomap"}
_GEO_DEFAULT_LAT = 51.0
_GEO_DEFAULT_LNG = 10.0
_GEO_DEFAULT_ZOOM = 5


def _parse_latlng(value: str | None) -> tuple[float, float] | None:
    """Parse a NagVis ``worldmap_center`` value (``"lat,lng"``) into floats.

    Not range-checked: NagVis saved Leaflet's centre, which runs past the
    antimeridian once the map is panned across it.
    """
    parts = (value or "").split(",")
    if len(parts) != 2:
        return None
    lat, lng = parse_degrees(parts[0]), parse_degrees(parts[1])
    return None if lat is None or lng is None else (lat, lng)


def _geo_view(p: dict[str, str]) -> GeoView:
    """Build a Maps geo view from a NagVis worldmap/geomap global block.

    Worldmap objects live in ``etc/worldmap.db`` and geomap hosts in a CSV — both
    are sidecar files the text-only map import can't read, so the UI import
    produces a correctly-framed but empty geo map. The CLI importer
    (tools/cfg_importer.py) fills the markers in from those sidecars.
    """
    lat, lng = _parse_latlng(p.get("worldmap_center")) or (_GEO_DEFAULT_LAT, _GEO_DEFAULT_LNG)
    zoom = p.get("worldmap_zoom") or p.get("geomap_zoom")
    lat, lng, zoom_level = bounded_view(lat, lng, _int(zoom, _GEO_DEFAULT_ZOOM))
    view: GeoView = {"type": "geo", "lat": lat, "lng": lng, "zoom": zoom_level}
    saturate = p.get("worldmap_tiles_saturate")
    if saturate not in (None, ""):
        view["tile_saturate"] = float(max(0, min(100, _int(saturate, 100))))
    return view


def _sources(p: Mapping[str, str]) -> set[str]:
    return {s.strip().lower() for s in p.get("sources", "").split(",") if s.strip()}


def _backends(raw: str) -> list[str]:
    return [b.strip() for b in raw.split(",") if b.strip()]


def _apply_global(map_cfg: MapPayload, p: dict[str, str], warnings: list[str]) -> None:
    if "alias" in p:
        map_cfg["alias"] = p["alias"]
    if p.get("map_image", "").lower() not in ("", "none"):
        map_cfg["background_image"] = p["map_image"]
    if background := _color(p.get("background_color"), ""):
        map_cfg["background_color"] = background
    # NagVis cfg uses the legacy "backend_id" parameter name on disk; map to our
    # canonical "connection_id" while reading.
    if backends := _backends(p.get("backend_id", "")):
        map_cfg["connection_id"] = backends[0]
        if len(backends) > 1:
            warnings.append(
                _(
                    "The map names several NagVis backends (%(backends)s). Maps reads from "
                    "one monitoring connection only; the others are ignored."
                )
                % {"backends": _clipped(", ".join(backends))}
            )
    if "iconset" in p:
        map_cfg["icon_size"] = ICONSET_SIZE.get(p["iconset"], 22)

    sources = _sources(p)
    if "automap" in sources:
        view: FlowView = {"type": "flow"}
        if p.get("root"):
            view["root"] = p["root"]
        # An unparseable depth is left unset rather than defaulted: -1 means
        # "unlimited" to the daemon, which is an expensive thing to inherit from a
        # typo, and an absent key simply keeps the daemon's own default.
        if (child_layers := _opt_int(p.get("child_layers"))) is not None:
            view["child_layers"] = _clamp(child_layers, -1, 20)
        if (parent_layers := _opt_int(p.get("parent_layers"))) is not None:
            view["parent_layers"] = _clamp(parent_layers, -1, 20)
        map_cfg["view"] = view
    elif sources & _GEO_SOURCES:
        map_cfg["view"] = _geo_view(p)


def _line_obj_common(p: dict[str, str], raw_id: str) -> _ImportObject:
    x, y, x2, y2, mid_x, mid_y = _line_coords(p)
    line_type = _int(p.get("line_type", "11"))
    payload: MapObject = {
        "id": f"line_{raw_id}",
        "type": "line",
        "x": x.value,
        "y": y.value,
        "x2": x2.value,
        "y2": y2.value,
        "label": _hidden_label(),
        "line_style": _LINE_STYLES.get(line_type, _DEFAULT_LINE_STYLE),
        # NagVis line_width is the polygon half-width (-w to +w); Maps renders
        # it as full stroke width. Double on import. The daemon's range starts at
        # 1, so an explicit line_width = 0 becomes a hairline instead of an
        # invisible line — Maps has no "hidden line" state, and the alternative
        # (dropping the object) would lose its bindings silently.
        "line_width": _clamp(_int(p.get("line_width"), 3) * 2, 1, 20),
    }
    if (perfdata_label := _LINE_PERFDATA_LABELS.get(line_type)) is not None:
        payload["line_perfdata_label"] = perfdata_label
        payload["line_weather_color"] = True
    if border := _color(p.get("line_color_border"), ""):
        payload["line_color_border"] = border
    _set_explicit_z(payload, p)
    refs: dict[_Axis, _Coord] = {"x": x, "y": y, "x2": x2, "y2": y2}
    # Explicit bend/meeting point (NagVis stored the middle of a 3-coord line).
    if mid_x is not None and mid_y is not None:
        payload["mid_x"] = mid_x.value
        payload["mid_y"] = mid_y.value
        refs["mid_x"] = mid_x
        refs["mid_y"] = mid_y
    obj = _ImportObject(payload, _pending(refs))
    # A line through a third point bends there instead.
    if (
        line_type in _SPLIT_LINE_TYPES
        and "mid_x" not in payload
        and _is_off_center_cut(p.get("line_cut"))
    ):
        obj.dropped["line_cut"] = ""
    return obj


# The line types NagVis draws in two halves, split in the middle unless
# ``line_cut`` says otherwise.
_SPLIT_LINE_TYPES = frozenset({10, 13, 14, 15})
_DEFAULT_LINE_CUT = 0.5


def _is_off_center_cut(raw: str | None) -> bool:
    if raw is None:
        return False
    try:
        return float(raw) != _DEFAULT_LINE_CUT
    except ValueError:
        return False


_LINE_PERFDATA_KEYS: tuple[
    Literal[
        "line_perfdata_label", "line_weather_color", "weathermap_metric", "weathermap_metric_out"
    ],
    ...,
] = ("line_perfdata_label", "line_weather_color", "weathermap_metric", "weathermap_metric_out")


def _apply_line_perfdata(obj: MapObject) -> None:
    """Keep a line's perfdata where it shows a service, with NagVis' in/out defaults.

    NagVis needs no metric configuration: line_label_in/line_label_out default
    to "in"/"out" and are matched against the bound service's perfdata. Maps
    requires an explicit weathermap_metric, so mirror that default — otherwise
    imported weathermap lines have the gradient enabled but no metric to read
    and stay uncolored.
    """
    if not (obj.get("host_name") and obj.get("service_description")):
        # NagVis reports the perfdata of such a line as missing.
        for key in _LINE_PERFDATA_KEYS:
            obj.pop(key, None)
        return
    if not obj.get("line_weather_color"):
        return
    obj.setdefault("weathermap_metric", "in")
    obj.setdefault("weathermap_metric_out", "out")


def _handle_view_type_line(block_type: str, p: dict[str, str], raw_id: str) -> _ImportObject:
    """Monitored object with view_type=line — a line in the object's state.

    Legacy format encodes a line this way; recognising it explicitly avoids
    the icon path treating the comma-separated x/y as broken coords.
    """
    obj = _line_obj_common(p, raw_id)
    _apply_links(obj.payload, p)
    _apply_type_specific(obj.payload, block_type, p)
    # A host or service line is implied by the fields it binds.
    if block_type not in ("host", "service"):
        obj.payload["line_object_type"] = _MONITOR_OBJECT_TYPES[block_type]
    # Legacy: line_label_in/out name the inbound/outbound perfdata fields so
    # the bandwidth labels can render flanking the midpoint.
    if "line_label_in" in p:
        obj.payload["weathermap_metric"] = p["line_label_in"]
    if "line_label_out" in p:
        obj.payload["weathermap_metric_out"] = p["line_label_out"]
    _apply_line_perfdata(obj.payload)
    return obj


def _handle_line_block(p: dict[str, str], raw_id: str) -> _ImportObject:
    obj = _line_obj_common(p, raw_id)
    _apply_links(obj.payload, p)
    # Stateful line variants (13/14/15) — bind to the service so live
    # bandwidth and weather-color have data to read from.
    if obj.payload.get("line_perfdata_label", "none") != "none" and p.get("service_description"):
        if "host_name" in p:
            obj.payload["host_name"] = p["host_name"]
        if "service_description" in p:
            obj.payload["service_description"] = p["service_description"]
        if "weathermap_metric" in p:
            obj.payload["weathermap_metric"] = p["weathermap_metric"]
        if "weathermap_metric_out" in p:
            obj.payload["weathermap_metric_out"] = p["weathermap_metric_out"]
    _apply_line_perfdata(obj.payload)
    if not obj.payload.get("host_name") and (color := _color(p.get("line_color"), "")):
        # A line without state has nothing else to colour it.
        obj.payload["line_color"] = color
    return obj


def _handle_shape(p: dict[str, str], raw_id: str) -> _ImportObject:
    x, y = _parse_coord(p.get("x", "0"), "x"), _parse_coord(p.get("y", "0"), "y")
    payload: MapObject = {
        "id": f"image_{raw_id}",
        "type": "image",
        "x": x.value,
        "y": y.value,
        "image_src": p.get("icon") or None,
        "label": _hidden_label(),
    }
    _set_explicit_z(payload, p)
    _apply_links(payload, p)
    return _ImportObject(payload, _pending({"x": x, "y": y}))


def _handle_container(p: dict[str, str], raw_id: str) -> _ImportObject:
    """NagVis ``container`` (embeds a URL's content) → Maps ``graph`` iframe.

    Maps has no dedicated container type; the graph object is the structural
    match — an iframe box at x/y with width/height.
    """
    x, y = _parse_coord(p.get("x", "0"), "x"), _parse_coord(p.get("y", "0"), "y")
    payload: MapObject = {
        "id": f"graph_{raw_id}",
        "type": "graph",
        "x": x.value,
        "y": y.value,
        "graph_url": p.get("url") or None,
        "graph_embed_type": "iframe",
        "graph_width": _int(p.get("w"), 400),
        "graph_height": _int(p.get("h"), 200),
        "label": _hidden_label(),
    }
    _set_explicit_z(payload, p)
    return _ImportObject(payload, _pending({"x": x, "y": y}))


# HTML <font size="N"> maps to fixed pixel sizes (legacy spec).
_FONT_SIZE_HTML = {"1": 10, "2": 13, "3": 16, "4": 18, "5": 24, "6": 32, "7": 48}
_FONT_SIZE_KEYWORD = {
    "xx-small": 9,
    "x-small": 10,
    "small": 13,
    "medium": 16,
    "large": 18,
    "x-large": 24,
    "xx-large": 32,
}

_TEXT_ALIGNS: dict[str, LabelAlign] = {value: value for value in get_args(LabelAlign)}
_TEXT_ALIGN_RE = rf"text-align\s*:\s*({'|'.join(_TEXT_ALIGNS)})"


class _HtmlStyle(TypedDict, total=False):
    """The label styling an inline-HTML textbox carries."""

    color: str
    size: int
    weight: LabelWeight
    align: LabelAlign


def _extract_html_style(html: str) -> _HtmlStyle:
    """Pull color/font-size/weight/text-align from inline HTML in a textbox."""
    out: _HtmlStyle = {}
    # "[^<>]" stops a tag at the next "<", which keeps the search linear in the text.
    m = re.search(r'<font[^<>]*color=["\']([^"\']+)', html, re.IGNORECASE)
    if not m:
        # Lookbehind keeps `background-color:` from matching as a `color:` suffix.
        m = re.search(r'(?<![-\w])color\s*:\s*([^;"\']+)', html, re.IGNORECASE)
    if m:
        out["color"] = m.group(1).strip()
    m = re.search(r'font-size\s*:\s*([^;"\']+)', html, re.IGNORECASE)
    if m:
        v = m.group(1).strip().lower()
        if v.endswith("px"):
            with contextlib.suppress(ValueError):
                out["size"] = int(float(v[:-2]))
        elif v in _FONT_SIZE_KEYWORD:
            out["size"] = _FONT_SIZE_KEYWORD[v]
    elif m := re.search(r'<font[^<>]*\bsize=["\']?([1-7])', html, re.IGNORECASE):
        out["size"] = _FONT_SIZE_HTML[m.group(1)]
    if re.search(r"<b\b", html, re.IGNORECASE) or re.search(
        r"font-weight\s*:\s*bold", html, re.IGNORECASE
    ):
        out["weight"] = "bold"
    if m := re.search(_TEXT_ALIGN_RE, html, re.IGNORECASE):
        out["align"] = _TEXT_ALIGNS[m.group(1).lower()]
    return out


# What of a textbox's HTML the import keeps: its text, line breaks and what
# _extract_html_style reads.
_KEPT_TAGS = frozenset({"br", "b", "font", "span", "div", "p"})
_KEPT_STYLES = frozenset({"color", "font-size", "font-weight", "text-align"})
_KEPT_FONT_ATTRIBUTES = frozenset({"color", "size"})
_TAG_RE = re.compile(r"<\s*/?\s*([a-zA-Z][\w-]*)([^<>]*)")
_ATTRIBUTE_RE = re.compile(r"""([\w-]+)\s*=\s*("[^"]*"|'[^']*'|[^\s"'>]*)""")
_STYLE_PROPERTY_RE = re.compile(r"([\w-]+)\s*:")


def _loses_html(text: str) -> bool:
    for name, attributes in _TAG_RE.findall(text):
        name = name.lower()
        if name not in _KEPT_TAGS:
            return True
        for attribute, value in _ATTRIBUTE_RE.findall(attributes):
            attribute = attribute.lower()
            if attribute == "style":
                if any(
                    prop.lower() not in _KEPT_STYLES for prop in _STYLE_PROPERTY_RE.findall(value)
                ):
                    return True
            elif name != "font" or attribute not in _KEPT_FONT_ATTRIBUTES:
                return True
    return False


def _handle_textbox(p: dict[str, str], raw_id: str) -> _ImportObject:
    raw_text = p.get("text") or None
    html_style: _HtmlStyle = {}
    loses_html = False
    if raw_text:
        loses_html = _loses_html(raw_text)
        html_style = _extract_html_style(raw_text)
        raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"<[^<>]+>", "", raw_text)
        # NagVis label text treats &nbsp; as a plain space (not U+00A0).
        raw_text = html.unescape(raw_text).replace("\xa0", " ")
    width = (
        _int(p.get("w"), 200) if (p.get("w") or "").strip().lower() not in {"auto", ""} else None
    )
    height = (
        _int(p.get("h"), 40) if (p.get("h") or "").strip().lower() not in {"auto", ""} else None
    )
    # nagvis_classic anchors top-left; keep raw NagVis coords for 1:1 layout.
    tx = _parse_coord(p.get("x", "0"), "x")
    ty = _parse_coord(p.get("y", "0"), "y")
    raw_bg = p.get("background_color")
    background = _color(raw_bg, "transparent")
    label: MapLabel = {
        **LABEL_FIELD_DEFAULTS,
        "text": raw_text,
        "size": html_style.get("size", LABEL_FIELD_DEFAULTS["size"]),
        "color": _color(html_style.get("color"), _text_color_on(raw_bg)),
    }
    if (weight := html_style.get("weight")) is not None:
        label["weight"] = weight
    if (align := html_style.get("align")) is not None:
        label["align"] = align
    payload: MapObject = {
        "id": f"textbox_{raw_id}",
        "type": "textbox",
        "x": tx.value,
        "y": ty.value,
        "label": label,
        "textbox_background": background,
    }
    _set_explicit_z(payload, p)
    if width is not None:
        payload["textbox_width"] = width
    if height is not None:
        payload["textbox_height"] = height
    if border := _color(p.get("border_color"), ""):
        payload["textbox_border"] = border
    obj = _ImportObject(payload, _pending({"x": tx, "y": ty}))
    if loses_html:
        obj.dropped["html_textbox"] = ""
    return obj


def _build_display(p: dict[str, str]) -> MapDisplay:
    view_type = p.get("view_type", "icon")
    if view_type == "text":
        return {"mode": "text"}
    if view_type != "gadget":
        return {"mode": "icon"}
    # Unknown values fall back to icon so the object stays visible.
    if (gadget_type := _GADGET_URL_MAP.get(_gadget_url(p))) is None:
        return {"mode": "icon"}
    display: MapDisplay = {"mode": "gadget", "gadget_type": gadget_type, "gadget_metric": None}
    # Maps sizes a gadget by its width and grows the height with it, so a gauge
    # gets NagVis' width and a bar its height.
    if (drawn := _nagvis_gadget_size(p)) is not None:
        width, height = drawn
        display["image_size"] = round(height / _BAR_TRACK_SHARE) if gadget_type == "bar" else width
    return display


def _gadget_url(p: dict[str, str]) -> str:
    # NagVis draws a gadget without a gadget_url as the speedometer.
    return p.get("gadget_url", "").strip() or "std_speedometer.php"


def _nagvis_gadget_size(p: dict[str, str]) -> tuple[int, int] | None:
    """How large NagVis draws the stock gadget, ``None`` for any other."""
    gadget_url = _gadget_url(p)
    if (size := _NAGVIS_GADGET_SIZES.get(gadget_url)) is None:
        return None
    scale = min(_int(p.get("gadget_scale"), 100), _GADGET_SCALE_MAX)
    if gadget_url in _UNSCALED_GADGETS or scale <= 0:
        scale = 100
    width, height = size
    return width * scale // 100, height * scale // 100


def _drawn_gadget_height(gadget_type: str, size: int) -> int:
    if gadget_type == "bar":
        return round(size * _BAR_HEIGHT_SHARE)
    return round(size * _GAUGE_HEIGHT_SHARE) + _GAUGE_CAPTION_HEIGHT


def _apply_type_specific(obj: MapObject, block_type: str, p: dict[str, str]) -> None:
    if block_type in ("host", "service", "hostgroup", "servicegroup", "dyngroup") and _bool(
        p.get("only_hard_states")
    ):
        obj["only_hard_states"] = True
    if block_type in ("host", "hostgroup"):
        # NagVis counts the services of hosts unless told not to.
        obj["recognize_services"] = _bool(p.get("recognize_services"), True)
    for key in ("exclude_members", "exclude_member_states"):
        if p.get(key):
            obj[key] = p[key]
    if block_type == "host":
        obj["host_name"] = p.get("host_name")
    elif block_type == "service":
        obj["host_name"] = p.get("host_name")
        obj["service_description"] = p.get("service_description")
    elif block_type == "hostgroup":
        obj["group_name"] = p.get("hostgroup_name") or p.get("group_name")
    elif block_type == "servicegroup":
        obj["group_name"] = p.get("servicegroup_name") or p.get("group_name")
    elif block_type == "map":
        obj["map_name"] = p.get("map_name")
    elif block_type == "aggr":
        # Newer .cfg exports write 'name='; older CLI imports used 'aggr_name='.
        obj["aggregation_id"] = p.get("aggr_name") or p.get("name")
        if "aggr_url" in p and "url" not in p:
            obj["url"] = p["aggr_url"]
    elif block_type == "dyngroup":
        ot = (p.get("object_types") or "host").strip().lower()
        obj["object_types"] = "service" if ot == "service" else "host"
        obj["object_filter"] = p.get("object_filter") or None
        if obj["object_types"] == "host":
            obj["recognize_services"] = _bool(p.get("recognize_services"), True)


def _handle_monitor_block(
    block_type: str, p: dict[str, str], raw_id: str, map_icon_size: int
) -> _ImportObject:
    """host / service / hostgroup / servicegroup / map / aggr."""
    maps_type = _MONITOR_OBJECT_TYPES[block_type]
    x, y = _parse_coord(p.get("x", "0"), "x"), _parse_coord(p.get("y", "0"), "y")
    display = _build_display(p)
    icon_size = map_icon_size
    if display["mode"] == "icon" and (own := ICONSET_SIZE.get(p.get("iconset", ""))):
        display["image_size"] = icon_size = own
    elif display["mode"] == "gadget" and (size := display.get("image_size")):
        icon_size = _drawn_gadget_height(display["gadget_type"], size)
    payload: MapObject = {
        "id": f"{maps_type}_{raw_id}",
        "type": maps_type,
        "x": x.value,
        "y": y.value,
        "label": _label(p, x.value, y.value, icon_size),
        "display": display,
    }
    if border := _color(p.get("label_border"), ""):
        payload["label_border"] = border
    _set_explicit_z(payload, p)
    _apply_type_specific(payload, block_type, p)
    _apply_links(payload, p)
    if (maxlen := _int(p.get("label_maxlen"))) > 0:
        payload["label_maxlen"] = maxlen
    axes: tuple[tuple[Literal["x", "y"], _Coord], ...] = (("x", x), ("y", y))
    label_at = {
        axis: at
        for axis, coord in axes
        if coord.ref is not None and (at := _label_map_coord(p.get(f"label_{axis}"))) is not None
    }
    obj = _ImportObject(payload, _pending({"x": x, "y": y}), label_at=label_at)
    if p.get("view_type") == "gadget" and display["mode"] != "gadget":
        obj.dropped["custom_gadget"] = ""
    iconset = p.get("iconset")
    if display["mode"] == "icon" and iconset is not None and iconset not in _STOCK_ICONSETS:
        obj.dropped["custom_iconset"] = iconset
    return obj


def _apply_links(payload: MapObject, p: dict[str, str]) -> None:
    if "url" in p:
        payload["url"] = p["url"]
    if "url_target" in p:
        raw_target = p["url_target"]
        payload["url_target"] = "_blank" if raw_target in _FRAMESET_TARGETS else raw_target
    if p.get("hover_url"):
        payload["hover_url"] = p["hover_url"]


# The macros NagVis fills into a label (ElementLabel.js), as the placeholders
# Maps fills in. NagVis leaves any other one as it is.
_LABEL_MACROS = {
    "alias": "{{alias}}",
    "service_description": "{{service}}",
    "output": "{{output}}",
    "perfdata": "{{perf_data}}",
}
# ``[name]`` is the host of a host or service and the group of a group; a map's
# label shows the map's title, for ``[alias]`` as for ``[name]``.
_NAME_PLACEHOLDERS = {
    "host": "{{host}}",
    "service": "{{host}}",
    "hostgroup": "{{group}}",
    "servicegroup": "{{group}}",
}
_MACRO_RE = re.compile(r"\[(\w+)\]")


def _translate_macros(label: MapLabel, block_type: str) -> None:
    if not (text := label.get("text")):
        return
    macros = {**_LABEL_MACROS, "name": _NAME_PLACEHOLDERS.get(block_type, "{{name}}")}
    if block_type == "map":
        macros["alias"] = "{{name}}"
    label["text"] = _MACRO_RE.sub(lambda m: macros.get(m.group(1), m.group(0)), text)


def _handle_object_block(
    block_type: str, p: dict[str, str], raw_id: str, map_icon_size: int
) -> _ImportObject | None:
    if p.get("view_type") == "line" and block_type in _MONITOR_OBJECT_TYPES:
        return _handle_view_type_line(block_type, p, raw_id)
    if block_type == "line":
        return _handle_line_block(p, raw_id)
    if block_type == "shape":
        return _handle_shape(p, raw_id)
    if block_type == "textbox":
        return _handle_textbox(p, raw_id)
    if block_type == "container":
        return _handle_container(p, raw_id)
    return _handle_monitor_block(block_type, p, raw_id, map_icon_size)


# ---------------------------------------------------------------------------
# Dynamic maps
# ---------------------------------------------------------------------------

# NagVis also knows group dynmaps; a Maps grid adds only hosts or services.
_DYNMAP_TYPES: dict[str, GridObjectType] = {"host": "host", "service": "service"}
# The column ``filter_group`` limits the members by, per member type.
_GROUP_COLUMNS: dict[GridObjectType, str] = {"host": "groups", "service": "host_groups"}
# Imported object ids carry a type prefix, so this one is always free.
_DYNMAP_GRID_ID = "dynmap"
# What a dynmap object carries anyway; anything else is a setting of its own.
_DYNMAP_IDENTITY_KEYS = frozenset(
    {"object_id", "host_name", "service_description", "x", "y", "backend_id", "use"}
)


# The backend NagVis reads where neither a map nor its configuration names one.
NAGVIS_DEFAULT_BACKEND: Final = "live_1"


@dataclass(frozen=True)
class _Dynmap:
    grid: MapObject
    object_types: GridObjectType
    # The map's, else those of the NagVis it came from.
    backends: tuple[str, ...]
    # Where NagVis lays the members out, as the file says, before the grid's
    # position and spacing are kept within what Maps takes.
    origin: tuple[int, int]
    step: tuple[int, int]


def _nagvis_object_id(key: str) -> str:
    """NagVis' ``GlobalMapCfg::genObjId``, which names the objects a dynmap adds."""
    digest = hashlib.sha1(key.encode(), usedforsecurity=False).hexdigest()
    # PHP would read "0e…" as a number in a comparison.
    return digest[1:7] if digest.startswith("0e") else digest[:6]


def _dynmap(
    p: dict[str, str],
    defaults: dict[str, str],
    icon_size: int,
    default_backend: str,
    warnings: list[str],
) -> _Dynmap | None:
    """The grid a NagVis dynamic map's global block describes, if Maps can show it."""
    sources = _sources(p)
    raw_type = p.get("dynmap_object_types", "").strip().lower()
    if "dynmap" not in sources or not raw_type:
        return None
    if "automap" in sources or sources & _GEO_SOURCES:
        warnings.append(
            _(
                "This NagVis map also adds objects from a Livestatus filter, which Maps "
                "does not combine with an automatic or a geographic map. Those objects "
                "were left out."
            )
        )
        return None
    if (object_types := _DYNMAP_TYPES.get(raw_type)) is None:
        warnings.append(
            _(
                "This NagVis map adds a %(type)s for each group a Livestatus filter "
                "matches. A grid in Maps adds only hosts or services, so those "
                "objects were left out."
            )
            % {"type": _clipped(raw_type)}
        )
        return None
    object_filter: str | None = None
    # Without a filter, or with an empty one, NagVis adds every object of the type.
    if (raw_filter := p.get("dynmap_object_filter", "")).strip() and (
        object_filter := _usable_filter(raw_filter, object_types)
    ) is None:
        _warn_unusable_filter(warnings, raw_filter)
        return None
    if "filter" in sources and (group := p.get("filter_group", "").strip()):
        raw_filter = f"{object_filter or ''}Filter: {_GROUP_COLUMNS[object_types]} >= {group}\n"
        # A second line could add an Or: that makes the group optional.
        if (
            len(group.replace("\\n", "\n").splitlines()) > 1
            or (object_filter := _usable_filter(raw_filter, object_types)) is None
        ):
            _warn_unusable_filter(warnings, raw_filter)
            return None

    offset_x = _int(p.get("dynmap_offset_x"), GRID_FIELD_DEFAULTS["grid_offset_x"])
    offset_y = _int(p.get("dynmap_offset_y"), GRID_FIELD_DEFAULTS["grid_offset_y"])
    # NagVis' dynmap_init_x/y defaults.
    init_x = _int(p.get("dynmap_init_x"), 20)
    init_y = _int(p.get("dynmap_init_y"), 700)
    grid: MapObject = {
        "id": _DYNMAP_GRID_ID,
        "type": "grid",
        "x": max(init_x, 0),
        "y": max(init_y, 0),
        "url_target": "_self",
        "object_types": object_types,
        "grid_per_row": _clamp(
            _int(p.get("dynmap_per_row"), GRID_FIELD_DEFAULTS["grid_per_row"]), 1, GRID_PER_ROW_MAX
        ),
        "grid_offset_x": _clamp(offset_x, 0, GRID_OFFSET_MAX),
        "grid_offset_y": _clamp(offset_y, 0, GRID_OFFSET_MAX),
        # NagVis sorts by name for anything but "s", "k" included.
        "grid_sort": "state" if p.get("dynmap_sort", "").strip() == "s" else "name",
        "grid_order": "desc" if p.get("dynmap_order", "").strip().lower() == "desc" else "asc",
    }
    if object_filter:
        grid["object_filter"] = object_filter
    _apply_member_look(grid, defaults, object_types, icon_size, warnings)
    backends = _backends(p.get("backend_id", "")) or _backends(default_backend)
    return _Dynmap(
        grid, object_types, tuple(backends), origin=(init_x, init_y), step=(offset_x, offset_y)
    )


# What a warning quotes from a cfg, which may be as long as the file.
_QUOTED_MAX_CHARS = 200


def _clipped(text: str) -> str:
    if len(text) <= _QUOTED_MAX_CHARS:
        return text
    return f"{text[:_QUOTED_MAX_CHARS]}… ({len(text)} characters)"


def _warn_unusable_filter(warnings: list[str], raw: str) -> None:
    warnings.append(
        _(
            "This NagVis map adds its objects from a Livestatus filter Maps cannot "
            'use: "%(filter)s". Those objects were left out.'
        )
        % {"filter": _clipped(raw)}
    )


def _usable_filter(raw: str, object_types: str | None) -> str | None:
    try:
        object_filter = normalize_object_filter(raw)
        check_object_filter(object_filter, object_types)
    except ValueError:
        return None
    return object_filter


def _apply_member_look(
    grid: MapObject,
    p: dict[str, str],
    object_types: GridObjectType,
    icon_size: int,
    warnings: list[str],
) -> None:
    """Gives the grid what the global block sets for every object, which its
    members take."""
    if any(_label_map_coord(p.get(key)) is not None for key in ("label_x", "label_y")):
        warnings.append(
            _(
                "The objects a filter adds put their labels at one point of the map. "
                "Maps puts each label at its own object."
            )
        )
        p = {k: v for k, v in p.items() if k not in ("label_x", "label_y")}
    label = _label(p, 0, 0, icon_size, show_default=False)
    if object_types == "service":
        # NagVis labels the services it adds with their names, whatever is set.
        label["text"] = "{{service}}"
    else:
        _translate_macros(label, object_types)
    grid["label"] = label
    if border := _color(p.get("label_border"), ""):
        grid["label_border"] = border
    if (max_length := _int(p.get("label_maxlen"))) > 0:
        grid["label_maxlen"] = max_length
    grid["only_hard_states"] = _bool(p.get("only_hard_states"))
    if object_types == "host":
        grid["recognize_services"] = _bool(p.get("recognize_services"), True)
    dropped: tuple[tuple[Literal["exclude_members", "exclude_member_states"], str], ...] = (
        (
            "exclude_members",
            _(
                "The objects a filter adds leave out members by a pattern Maps cannot "
                "apply. The pattern was dropped."
            ),
        ),
        (
            "exclude_member_states",
            _(
                "The objects a filter adds ignore the state of some members by a pattern "
                "Maps cannot apply. Maps counts every member; the setting was dropped."
            ),
        ),
    )
    for key, warning in dropped:
        if not (pattern := p.get(key)):
            continue
        if object_types == "host" and (kept := _member_pattern("host", pattern)) is not None:
            grid[key] = kept
        else:
            warnings.append(warning)


def _dynmap_key(block_type: str, p: dict[str, str]) -> str:
    host = p.get("host_name", "")
    return f"{host}~~{p.get('service_description', '')}" if block_type == "service" else host


def _in_dynmap_grid(dynmap: _Dynmap, p: dict[str, str]) -> bool:
    """NagVis' ``dynmap_object_in_grid``, which leaves the first row and column out."""
    dx = _int(p.get("x")) - dynmap.origin[0]
    dy = _int(p.get("y")) - dynmap.origin[1]
    step_x, step_y = dynmap.step
    return step_x > 0 and step_y > 0 and dx > 0 and dx % step_x == 0 and dy > 0 and dy % step_y == 0


def _dynmap_part(
    dynmap: _Dynmap, block_type: str, block: dict[str, str], effective: dict[str, str]
) -> Literal["pinned", "grid", "stale"] | None:
    """What a file object of the dynmap's type is to NagVis.

    ``stale`` is one NagVis deletes, as no member has its id; ``grid`` one it lays
    out with the members; ``pinned`` one the operator moved off the grid. ``None``
    for an object of another type.
    """
    if block_type != dynmap.object_types:
        return None
    key = _dynmap_key(block_type, effective)
    ids = {_nagvis_object_id(f"{backend}~~{key}") for backend in dynmap.backends}
    if ids and block.get("object_id") not in ids:
        return "stale"
    return "grid" if _in_dynmap_grid(dynmap, effective) else "pinned"


def _dynmap_warnings(stale: int, customized: int, lines: int) -> list[str]:
    warnings: list[str] = []
    if lines:
        warnings.append(
            ungettext(
                "%(count)d object the filter adds is drawn as a line. Maps shows it as a "
                "line and in the grid, too.",
                "%(count)d objects the filter adds are drawn as lines. Maps shows them as "
                "lines and in the grid, too.",
                lines,
            )
            % {"count": lines}
        )
    if stale:
        warnings.append(
            ungettext(
                "%(count)d object of the type the filter adds is not one the filter "
                "added. NagVis does not show it, so it was left out.",
                "%(count)d objects of the type the filter adds are not ones the filter "
                "added. NagVis does not show them, so they were left out.",
                stale,
            )
            % {"count": stale}
        )
    if customized:
        warnings.append(
            ungettext(
                "%(count)d object the filter adds had settings of its own. Maps shows "
                "every such object as the map's settings say.",
                "%(count)d objects the filter adds had settings of their own. Maps shows "
                "every such object as the map's settings say.",
                customized,
            )
            % {"count": customized}
        )
    return warnings


def convert_cfg(
    content: str, map_name: str, default_backend: str = NAGVIS_DEFAULT_BACKEND
) -> tuple[MapPayload, list[str]]:
    """Convert legacy .cfg text to a Maps map, with what it could not carry over.

    ``default_backend`` is the one the NagVis the map comes from used where the map
    names none, for the ids of the objects a dynamic map added.
    """
    warnings: list[str] = []
    map_cfg: MapPayload = {
        "name": map_name,
        "alias": map_name,
        # Empty until the global block names a backend: NagVis then used its default
        # backend, which resolve_connection_ids turns into this site's default.
        "connection_id": "",
        "icon_size": 22,
        "rotation_interval": MAP_FIELD_DEFAULTS["rotation_interval"],
        "hover_template": None,
        "context_template": None,
        "background_image": None,
        # NagVis has no equivalent knobs.
        "sort_order": MAP_FIELD_DEFAULTS["sort_order"],
        "click_action": MAP_FIELD_DEFAULTS["click_action"],
        # cfg-imports keep NagVis' geometry: top-left anchoring, native background.
        "render_mode": "nagvis_classic",
        # NagVis' global default z is 10 for every object type and is never
        # written per-object; objects without an explicit z inherit this.
        "default_z": 10,
        "background_style": MAP_FIELD_DEFAULTS["background_style"],
        "background_position": MAP_FIELD_DEFAULTS["background_position"],
        "view": {"type": "static"},
        "objects": [],
    }
    objects: list[_ImportObject] = []
    counter = 0

    blocks = _parse_blocks(content)
    if sum(1 for block_type, _p in blocks if block_type in _BLOCK_TYPES) > _MAX_CFG_OBJECTS:
        raise MKUserError(
            "file",
            _("The map contains more than %(limit)d objects.") % {"limit": _MAX_CFG_OBJECTS},
        )

    # NagVis resolves each parameter as object > template (``use=name``) >
    # global > built-in default.
    global_props: dict[str, str] = {}
    for block_type, p in blocks:
        if block_type == "global":
            global_props = p
    global_defaults = {
        k: v
        for k, v in global_props.items()
        if k not in _NON_INHERITED_KEYS and k not in _GLOBAL_MAP_KEYS
    }
    map_icon_size = ICONSET_SIZE.get(global_props.get("iconset", ""), 22)
    dynmap = _dynmap(global_props, global_defaults, map_icon_size, default_backend, warnings)
    stale = customized = lines = settings_chars = 0
    features = _Features()
    warnings += _unknown_type_warnings(blocks)

    for (block_type, p), with_template in zip(blocks, _merge_templates(blocks), strict=True):
        if block_type == "global":
            _apply_global(map_cfg, p, warnings)
            continue
        if block_type not in _BLOCK_TYPES:
            continue
        counter += 1
        # object_id identifies the object and is never inherited.
        object_id = p.get("object_id")
        raw_id = object_id or str(counter)
        effective = {**global_defaults, **with_template}
        effective.pop("use", None)
        settings_chars += sum(len(k) + len(v) for k, v in effective.items())
        if settings_chars > _MAX_OBJECT_SETTINGS_CHARS:
            raise MKUserError(
                "file",
                _(
                    "The objects of the map, with what their templates and the global"
                    " settings pass on, take more than %(limit)d characters."
                )
                % {"limit": _MAX_OBJECT_SETTINGS_CHARS},
            )
        part = _dynmap_part(dynmap, block_type, p, effective) if dynmap else None
        if part == "stale":
            stale += 1
            continue
        if part == "grid":
            customized += bool(with_template.keys() - _DYNMAP_IDENTITY_KEYS)
            continue
        obj = _handle_object_block(block_type, effective, raw_id, map_icon_size)
        if obj is not None:
            # ``url_target`` is a required field on every map object; only the
            # monitor handler sets it (and only when the cfg gave a target). Give
            # everything else NagVis' default so the map round-trips on save.
            obj.payload.setdefault("url_target", "_self")
            if block_type in _MONITOR_OBJECT_TYPES and (label := obj.payload.get("label")):
                _translate_macros(label, block_type)
            # NagVis allows backend_id per object so one map can mix monitoring
            # sources; the daemon honours that (it groups the state fetch by
            # connection). Kept raw here and resolved against the configured
            # connections in resolve_connection_ids, like the map-level id.
            if backend := effective.get("backend_id") or effective.get("connection_id"):
                obj.payload["connection_id"] = backend
            if part == "pinned" and obj.payload["type"] in ("host", "service"):
                obj.payload["grid_id"] = _DYNMAP_GRID_ID
            elif part == "pinned":
                # Only a host or a service is pinned out of a grid.
                lines += 1
            obj.ref_id = object_id
            objects.append(obj)
            features.add(obj, block_type, effective)

    _resolve_pending_refs(objects)

    warnings += _global_warnings(global_props, map_cfg["view"]["type"])
    if map_cfg["view"]["type"] == "flow":
        warnings += _automap_object_warnings(len(objects))
    if map_cfg["view"]["type"] in ("flow", "geo"):
        # Flow auto-populates from topology; worldmap markers come from a sidecar
        # file (worldmap.db / geomap CSV) the text-only import can't read, so the
        # map is framed here and filled by the CLI importer.
        objects = []
    else:
        warnings += features.warnings()
    # NagVis lets a cfg repeat an object_id, and an explicit one can match the
    # counter of a block without one.
    for obj, object_id in zip(
        objects, unique_ids([obj.payload["id"] for obj in objects]), strict=True
    ):
        obj.payload["id"] = object_id
    map_cfg["objects"] = [obj.payload for obj in objects]
    if dynmap:
        # First, so its members are drawn over it.
        map_cfg["objects"].insert(0, dynmap.grid)
        warnings += _dynmap_warnings(stale, customized, lines)
    warnings += _host_group_warnings(global_props, map_cfg["objects"])
    return map_cfg, warnings


def _host_group_warnings(p: dict[str, str], objects: list[MapObject]) -> list[str]:
    """NagVis' ``filter`` source leaves out every object of a host outside the
    group, which only a grid of Maps can do."""
    group = p.get("filter_group", "").strip()
    if "filter" not in _sources(p) or not group:
        return []
    # Only the grid's own filter takes the group, not what is pinned out of it.
    if not any(obj.get("host_name") for obj in objects if obj["type"] != "grid"):
        return []
    return [
        _("NagVis left out the objects of hosts outside the host group %(group)s. Maps shows them.")
        % {"group": _clipped(group)}
    ]


# ---------------------------------------------------------------------------
# NagVis features Maps does not support
# ---------------------------------------------------------------------------

# The sources NagVis ships; any other is a plugin of that NagVis.
_KNOWN_SOURCES = frozenset({"automap", "dynmap", "filter", *_GEO_SOURCES})
# What NagVis sets for an automap beyond its root and layers, with its defaults.
_AUTOMAP_DEFAULTS = {
    "render_mode": "undirected",
    "rankdir": "LR",
    "overlap": "scale",
    "margin": "50",
    "ignore_hosts": "",
    "filter_by_state": "0",
    "filter_by_ids": "",
}
# The blocks of a map file that are no object of the map.
_STRUCTURAL_BLOCKS = frozenset({"global", "template"})
_DEFAULT_TEMPLATE = "default"


def _names(values: Collection[str]) -> str:
    return _clipped(", ".join(sorted(values)))


def _global_warnings(p: Mapping[str, str], view_type: str) -> list[str]:
    """What the global block of a map sets that Maps does not carry over."""
    warnings: list[str] = []
    sources = _sources(p)
    if unknown := sources - _KNOWN_SOURCES:
        warnings.append(
            _(
                "The map takes objects from NagVis sources Maps does not have: %(sources)s. Add "
                "these objects in the editor, for example as a grid with a Livestatus filter."
            )
            % {"sources": _names(unknown)}
        )
    if "automap" in sources and (
        settings := {
            key
            for key, default in _AUTOMAP_DEFAULTS.items()
            if p.get(key, default).strip() not in ("", default)
        }
    ):
        warnings.append(
            _(
                "Maps lays out a flow map itself and does not carry over these automap layout "
                "options: %(settings)s"
            )
            % {"settings": _names(settings)}
        )
    if (
        view_type == "static"
        and (iconset := p.get("iconset")) is not None
        and iconset not in _STOCK_ICONSETS
    ):
        warnings.append(
            _(
                "The map uses the custom icon set '%(name)s', so its objects show the state icon "
                "of Maps. To give them a look of their own, choose an image from the image "
                "library."
            )
            % {"name": _clipped(iconset)}
        )
    if (template := p.get("header_template", _DEFAULT_TEMPLATE)) != _DEFAULT_TEMPLATE:
        warnings.append(
            _(
                "The map uses the NagVis header template file '%(name)s'. Maps shows its own "
                "header. Put what the template showed on the map, for example as textboxes or "
                "links."
            )
            % {"name": _clipped(template)}
        )
    if _bool(p.get("event_sound")) or _bool(p.get("event_log")):
        warnings.append(
            _(
                "The map plays a sound or keeps an event log when a state changes. Maps does "
                "neither. Use notifications instead."
            )
        )
    return warnings


def _unknown_type_warnings(blocks: Sequence[tuple[str, Mapping[str, str]]]) -> list[str]:
    unknown = Counter(
        block_type
        for block_type, _p in blocks
        if block_type not in _BLOCK_TYPES and block_type not in _STRUCTURAL_BLOCKS
    )
    if not (count := unknown.total()):
        return []
    return [
        ungettext(
            "%(count)d object of an unknown type was left out: %(types)s. Add it in the editor as "
            "an object Maps has.",
            "%(count)d objects of unknown types were left out: %(types)s. Add them in the editor "
            "as objects Maps has.",
            count,
        )
        % {"count": count, "types": _names(unknown)}
    ]


def _automap_object_warnings(count: int) -> list[str]:
    if not count:
        return []
    return [
        ungettext(
            "%(count)d object of the automap file was left out, as Maps lays out a flow map "
            "itself.",
            "%(count)d objects of the automap file were left out, as Maps lays out a flow map "
            "itself.",
            count,
        )
        % {"count": count}
    ]


@dataclass
class _Features:
    """Counts what the imported objects use that Maps does not carry over."""

    dropped: Counter[_Dropped] = field(default_factory=Counter)
    iconsets: set[str] = field(default_factory=set)
    hover_urls: int = 0
    macro_links: int = 0
    hover_templates: Counter[str] = field(default_factory=Counter)
    context_templates: Counter[str] = field(default_factory=Counter)

    def add(self, obj: _ImportObject, block_type: str, p: Mapping[str, str]) -> None:
        self.dropped.update(obj.dropped.keys())
        if iconset := obj.dropped.get("custom_iconset"):
            self.iconsets.add(iconset)
        self.hover_urls += bool((url := p.get("hover_url")) and coerce_user_url(url) is not None)
        self.macro_links += sum(
            bool(_MACRO_RE.search(link)) and coerce_user_url(link) is not None
            for key in ("url", "hover_url")
            if (link := p.get(key))
        )
        if block_type not in _MONITOR_OBJECT_TYPES:
            return
        if (template := p.get("hover_template", _DEFAULT_TEMPLATE)) != _DEFAULT_TEMPLATE:
            self.hover_templates[template] += 1
        if (template := p.get("context_template", _DEFAULT_TEMPLATE)) != _DEFAULT_TEMPLATE:
            self.context_templates[template] += 1

    def warnings(self) -> list[str]:
        """Name each feature with the objects it affects and what to do about it."""
        warnings: list[str] = []
        if count := self.dropped["custom_gadget"]:
            warnings.append(
                ungettext(
                    "%(count)d custom gadget is shown as an icon. Choose a gadget type in "
                    "the editor.",
                    "%(count)d custom gadgets are shown as icons. Choose a gadget type in "
                    "the editor.",
                    count,
                )
                % {"count": count}
            )
        if count := self.dropped["html_textbox"]:
            warnings.append(
                ungettext(
                    "%(count)d HTML textbox keeps its text, bold, color, size and alignment, but "
                    "loses the rest of its HTML. Use plain text, or a hover template for "
                    "formatted content.",
                    "%(count)d HTML textboxes keep their text, bold, color, size and alignment, "
                    "but lose the rest of their HTML. Use plain text, or a hover template for "
                    "formatted content.",
                    count,
                )
                % {"count": count}
            )
        if count := self.hover_urls:
            warnings.append(
                ungettext(
                    "%(count)d object has a hover URL. Maps keeps it, but does not show it "
                    "on hover. Put the content into a hover template.",
                    "%(count)d objects have a hover URL. Maps keeps them, but does not show "
                    "them on hover. Put the content into a hover template.",
                    count,
                )
                % {"count": count}
            )
        if count := self.macro_links:
            warnings.append(
                ungettext(
                    "%(count)d link uses NagVis macros such as [name], which Maps does not fill "
                    "in. Write the link without macros.",
                    "%(count)d links use NagVis macros such as [name], which Maps does not fill "
                    "in. Write the links without macros.",
                    count,
                )
                % {"count": count}
            )
        if count := self.hover_templates.total():
            warnings.append(
                ungettext(
                    "%(count)d object uses a NagVis hover template file, which Maps does not "
                    "have: %(names)s. Paste the markup into the hover template of the map or the "
                    "object.",
                    "%(count)d objects use NagVis hover template files, which Maps does not have: "
                    "%(names)s. Paste the markup into the hover template of the map or the "
                    "objects.",
                    count,
                )
                % {"count": count, "names": _names(self.hover_templates)}
            )
        if count := self.context_templates.total():
            warnings.append(
                ungettext(
                    "%(count)d object uses a NagVis context template file, which Maps does not "
                    "have: %(names)s. Paste the markup into the context template of the map or "
                    "the object.",
                    "%(count)d objects use NagVis context template files, which Maps does not "
                    "have: %(names)s. Paste the markup into the context template of the map or "
                    "the objects.",
                    count,
                )
                % {"count": count, "names": _names(self.context_templates)}
            )
        if count := self.dropped["custom_iconset"]:
            warnings.append(
                ungettext(
                    "%(count)d object uses a custom icon set and shows the state icon of Maps: "
                    "%(names)s. To give it a look of its own, choose an image from the image "
                    "library.",
                    "%(count)d objects use custom icon sets and show the state icon of Maps: "
                    "%(names)s. To give them a look of their own, choose an image from the image "
                    "library.",
                    count,
                )
                % {"count": count, "names": _names(self.iconsets)}
            )
        if count := self.dropped["line_cut"]:
            warnings.append(
                ungettext(
                    "%(count)d line is split elsewhere than in its middle (line_cut). Maps splits "
                    "it in the middle. To split it where NagVis did, drag its middle in the "
                    "editor.",
                    "%(count)d lines are split elsewhere than in their middle (line_cut). Maps "
                    "splits them in the middle. To split them where NagVis did, drag their middle "
                    "in the editor.",
                    count,
                )
                % {"count": count}
            )
        return warnings


# ---------------------------------------------------------------------------
# GUI endpoint
# ---------------------------------------------------------------------------


def map_name_from_filename(filename: str) -> str:
    """Derive a map name the store and the daemon both accept from the upload."""
    stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(filename).stem)
    return stem[:MAP_NAME_MAX_LENGTH] or "imported_map"


def _configured_connection_ids() -> list[str]:
    """Connection ids from the WATO-owned ``maps_connections`` global.

    The import remaps a .cfg's ``backend_id`` to a real local connection like the
    legacy path did. The daemon used to resolve this against its live registry;
    the GUI owns the connection config, so read the configured list here.
    """
    return [cid for cid, _label in connection_choices()]


def _connection_for_backend(backend: str, configured: Sequence[str]) -> str:
    """The connection that is the same source as a NagVis backend.

    NagVis on a Checkmk site names its backends after the site (``<site>``, plus
    ``<site>_bi`` for BI aggregations), and Maps names the site's connection
    ``cmk_<site>``. A site whose own name ends in ``_bi`` wins over the BI backend
    of another. Any other name is returned unchanged.
    """
    for candidate in (backend, f"cmk_{backend}", f"cmk_{backend.removesuffix('_bi')}"):
        if candidate in configured:
            return candidate
    return backend


def resolve_connection_ids(
    map_cfg: MapPayload, configured: Sequence[str], default: str
) -> list[str]:
    """Point the map and its objects at connections that exist here; report what changed.

    A map without a backend gets ``default``, the connection new maps use: NagVis
    used its own default backend for it, which is no choice worth reporting.

    A ``.cfg`` names the backends of the NagVis installation it came from, which
    need not exist on this site. The map falls back to the first configured
    connection, as the legacy import did. A per-object override naming no
    configured connection is *dropped* so the object inherits the map's: pointing
    it at some other connection would resolve it against a same-named host on the
    wrong site and report that host's state as if it were the right one, which is
    worse than the whole map visibly sitting on one connection.

    Returns one ready-to-show message per thing the operator has to know, because
    both fallbacks are silent guesses otherwise.

    ``configured`` is passed in rather than read here: the endpoint is the only
    place that has to reach into the WATO globals, which keeps this resolvable
    against a plain list of ids.
    """
    warnings: list[str] = []

    named_map_id = map_cfg["connection_id"]
    requested_map_id = named_map_id or default
    map_id = _connection_for_backend(requested_map_id, configured)
    if map_id not in configured and configured:
        map_id = configured[0]
        if named_map_id:
            warnings.append(
                _(
                    "The map's monitoring connection %(requested)r is not configured here. "
                    "The map now uses %(used)r."
                )
                % {"requested": requested_map_id, "used": map_id}
            )
    map_cfg["connection_id"] = map_id

    inherited = {requested_map_id, map_id}
    dropped: Counter[str] = Counter()
    for obj in map_cfg["objects"]:
        if (raw := obj.pop("connection_id", None)) is None:
            continue
        override = _connection_for_backend(raw, configured)
        if override in inherited:
            # Same source as the map — an override would be redundant.
            continue
        if override in configured:
            obj["connection_id"] = override
        else:
            dropped[override] += 1

    for requested, count in sorted(dropped.items()):
        warnings.append(
            ungettext(
                "%(count)d object uses the monitoring connection %(requested)r, which is "
                "not configured here. It now uses the map's connection.",
                "%(count)d objects use the monitoring connection %(requested)r, which is "
                "not configured here. They now use the map's connection.",
                count,
            )
            % {"count": count, "requested": requested}
        )
    return warnings


@dataclass(frozen=True)
class ImportSite:
    """The site a map is imported on: its own connection, and whether it is
    one of several, which a NagVis map of one backend does not cover alike."""

    connection: str
    distributed: bool


def parse_cfg_upload(
    filename: str, contents: bytes, site: ImportSite, default_backend: str
) -> tuple[MapPayload, list[str]]:
    """Parse an uploaded legacy NagVis ``.cfg`` into a map dict (no persistence).

    The returned map is a draft the editor shows before the user saves it through
    the Maps REST API. Parsing is stateless format knowledge, so this needs no
    daemon round-trip.

    Connection ids are remapped onto the configured local connections (as the
    legacy import did), and every such guess is named in the warnings so the
    operator can correct the map instead of wondering why an object stays
    PENDING.
    """
    if not filename or not filename.lower().endswith(".cfg"):
        raise MKUserError("filename", _("Only .cfg files are accepted."))
    if len(contents) > MAX_CFG_BYTES:
        raise MKUserError(
            "content",
            _("The uploaded file is too large (maximum %(limit)d MB).")
            % {"limit": MAX_CFG_BYTES // (1024 * 1024)},
        )
    map_cfg, warnings = convert_cfg(
        decode_cfg(contents), map_name_from_filename(filename), default_backend
    )
    return map_cfg, (
        resolve_connection_ids(
            map_cfg, _configured_connection_ids(), map_object_defaults()["default_backend_id"]
        )
        + warnings
        + drop_unusable_urls(map_cfg)
        + drop_member_filters(map_cfg)
        + drop_unusable_filters(map_cfg)
        + grid_site_warnings(map_cfg, site.connection, distributed=site.distributed)
    )


def grid_site_warnings(
    map_cfg: MapPayload, site_connection: str, *, distributed: bool
) -> list[str]:
    """NagVis takes a dynamic map's objects from one backend, which is one site;
    the site's connection of Maps covers every site of a distributed setup."""
    if not distributed or not any(
        obj["type"] == "grid"
        and (obj.get("connection_id") or map_cfg["connection_id"]) == site_connection
        for obj in map_cfg["objects"]
    ):
        return []
    return [
        _(
            "NagVis added the objects of the filter from one site. Maps adds those of "
            "every site of the connection."
        )
    ]


_URL_KEYS: tuple[Literal["url", "hover_url", "graph_url"], ...] = ("url", "hover_url", "graph_url")


def drop_unusable_urls(map_cfg: MapPayload) -> list[str]:
    """Drop the links Maps does not accept, with a warning that counts them.

    Saving the imported map validates every link, so a single one Maps rejects
    (``javascript:``, ``//host/...``) would fail the whole import.
    """
    dropped = 0
    for obj in map_cfg["objects"]:
        for key in _URL_KEYS:
            coerce = coerce_graph_url if key == "graph_url" else coerce_user_url
            if obj.get(key) and coerce(obj[key]) is None:
                del obj[key]
                dropped += 1
    if not dropped:
        return []
    return [
        ungettext(
            "%(count)d link uses an address Maps does not accept. It was dropped.",
            "%(count)d links use an address Maps does not accept. They were dropped.",
            dropped,
        )
        % {"count": dropped}
    ]


def drop_unusable_filters(map_cfg: MapPayload) -> list[str]:
    """Leave out the objects whose Livestatus filter Maps cannot use, counting them.

    Saving the imported map would refuse the filter, and without it the object
    would show every host or service instead of those it names.
    """
    kept: list[MapObject] = []
    for obj in map_cfg["objects"]:
        if raw := obj.get("object_filter"):
            if (object_filter := _usable_filter(raw, obj.get("object_types"))) is None:
                continue
            obj["object_filter"] = object_filter
        kept.append(obj)
    if not (dropped := len(map_cfg["objects"]) - len(kept)):
        return []
    map_cfg["objects"] = kept
    return [
        ungettext(
            "%(count)d object shows what a Livestatus filter Maps cannot use matches. "
            "It was left out.",
            "%(count)d objects show what a Livestatus filter Maps cannot use matches. "
            "They were left out.",
            dropped,
        )
        % {"count": dropped}
    ]


def drop_member_filters(map_cfg: MapPayload) -> list[str]:
    """Drop the member filters Maps cannot apply, counting them in the warnings.

    Maps leaves out members of a host, a host group and a service group as
    NagVis does. A pattern anywhere else, or one Maps would reject, would only
    mislead whoever reads the object later.
    """
    warnings: list[str] = []
    if members := _drop_inapplicable(map_cfg, "exclude_members"):
        warnings.append(
            ungettext(
                "%(count)d object leaves out members by a pattern Maps cannot apply. "
                "The pattern was dropped.",
                "%(count)d objects leave out members by a pattern Maps cannot apply. "
                "The patterns were dropped.",
                members,
            )
            % {"count": members}
        )
    if states := _drop_inapplicable(map_cfg, "exclude_member_states"):
        warnings.append(
            ungettext(
                "%(count)d object ignores the state of some members by a pattern Maps "
                "cannot apply. Maps counts every member; the setting was dropped.",
                "%(count)d objects ignore the state of some members by a pattern Maps "
                "cannot apply. Maps counts every member; the settings were dropped.",
                states,
            )
            % {"count": states}
        )
    if warnings:
        warnings.append(
            _(
                "Maps applies such a pattern only to hosts, host groups and service groups, "
                "only as a single line of at most %(max)d characters, and never as "
                "host~~service on a host."
            )
            % {"max": MEMBER_PATTERN_MAX_LENGTH}
        )
    return warnings


def _drop_inapplicable(
    map_cfg: MapPayload, key: Literal["exclude_members", "exclude_member_states"]
) -> int:
    dropped = 0
    for obj in map_cfg["objects"]:
        if not (pattern := obj.get(key)):
            continue
        if (kept := _applicable_member_pattern(obj, pattern)) is None:
            del obj[key]
            dropped += 1
        else:
            obj[key] = kept
    return dropped


def _applicable_member_pattern(obj: MapObject, pattern: str) -> str | None:
    """*pattern* as Maps stores it, or ``None`` where Maps does not apply it."""
    bound = bound_type_of(obj["type"], obj.get("line_object_type"), obj.get("service_description"))
    if bound not in ("host", "hostgroup", "servicegroup"):
        return None
    return _member_pattern(bound, pattern)


def _member_pattern(bound: str, pattern: str) -> str | None:
    try:
        check_host_member_patterns(bound, pattern)
        return validate_member_pattern(pattern)
    except ValueError:
        return None


def decode_cfg(contents: bytes) -> str:
    """NagVis reads a file that is no valid UTF-8 as ISO-8859-1, as older maps were saved."""
    contents = contents.removeprefix(codecs.BOM_UTF8)
    try:
        return contents.decode("utf-8")
    except UnicodeDecodeError:
        return contents.decode("iso-8859-1")
