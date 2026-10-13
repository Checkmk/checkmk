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

import contextlib
import html
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import get_args, Literal, TypedDict

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _, ungettext
from cmk.maps.gui._settings import connection_choices
from cmk.maps.shared.map_payload import (
    FlowView,
    GadgetType,
    LabelAlign,
    LabelWeight,
    LinePerfdataLabel,
    LineStyle,
    MapDisplay,
    MapLabel,
    MapObject,
    MapPayload,
    ObjectType,
    WorldmapView,
)
from cmk.maps.shared.validators import coerce_color

# A NagVis .cfg is a small text file; cap the upload before the whole-file regex
# scan + multi-pass reference resolver run over it, mirroring the icon/background
# upload caps. Real exported maps are well under this.
MAX_CFG_BYTES = 5 * 1024 * 1024  # 5 MB

# The byte cap alone does not bound the result: one ~25-byte `define` block
# becomes a full map object in the JSON response, so a 5 MB file of tiny blocks
# would balloon the draft the SPA has to hold. Real exported maps stay well below
# this; an automap this large is unusable as a map anyway.
_MAX_CFG_OBJECTS = 2000

# Mirrors the daemon's MapConfig.name constraint.
_MAX_MAP_NAME_LEN = 100


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

# 13/14/15 only appear on stateful lines (service block with view_type=line) and
# are the only ones that carry perfdata labels — always with the weather gradient.
_LINE_PERFDATA_LABELS: dict[int, LinePerfdataLabel] = {
    13: "percent",
    14: "both",
    15: "bandwidth",
}

ICONSET_SIZE: dict[str, int] = {
    "std_big": 30,
    "std_medium": 24,
    "std": 22,
    "std_small": 16,
}

_FRAMESET_TARGETS = {"main", "frames", "main_window"}

# Stock legacy gadget URL → Maps gadget_type. Custom/unknown gadget_urls
# fall back to icon mode silently — there is no equivalent Maps renderer.
_GADGET_URL_MAP: dict[str, GadgetType] = {
    "std_speedometer.php": "gauge",
    "std_speedometer2.php": "gauge",
    "std_bar.php": "bar",
    "std_html_bar.php": "bar",
    "rawNumbers.php": "value",
}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _parse_blocks(text: str) -> list[tuple[str, dict[str, str]]]:
    text = re.sub(r"(?m)^\s*#[^\n]*", "", text)
    text = re.sub(r"(?m)^\s*;[^\n]*", "", text)
    blocks = []
    for m in re.finditer(r"define\s+(\w+)\s*\{([^}]*)\}", text, re.DOTALL):
        block_type = m.group(1).strip().lower()
        props: dict[str, str] = {}
        for line in m.group(2).splitlines():
            line = line.strip()
            kv = re.match(r"(\w+)\s*=\s*(.*)", line)
            if kv:
                props[kv.group(1).strip()] = kv.group(2).strip()
        blocks.append((block_type, props))
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


# NagVis [name] macro resolves to the object identifier; Maps uses
# {{name}}. Dropping the label lets the renderer fall back to host_name
# rather than printing the literal token.
_BARE_NAME_RE = re.compile(r"^\s*\[name\]\s*$")


def _label_text(raw: str | None) -> str | None:
    if not raw:
        return None
    if _BARE_NAME_RE.match(raw):
        return None
    return raw


def _label_x(raw: str | None) -> int:
    """Parse legacy ``label_x``. NagVis allows ``center`` to mean 0-offset."""
    if raw is None:
        return 0
    v = raw.strip().lower()
    if v == "center":
        return 0
    try:
        return int(v.lstrip("+"))
    except ValueError:
        return 0


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


def _label_y(raw: str | None) -> int:
    """Parse legacy ``label_y``.

    NagVis defaults to ``bottom`` which places the label top flush with the
    icon's bottom edge — that's ``label_top = object_y + icon_height``. With
    Maps' 22-px default icon that's 22. Anything explicit (``+25``, ``-3``,
    ``0``) is honoured as a relative pixel offset.
    """
    if raw is None:
        return 22
    v = raw.strip().lower()
    if v in ("", "bottom"):
        return 22
    if v == "top":
        return 0
    if v == "center":
        return -11
    try:
        return int(v.lstrip("+"))
    except ValueError:
        return 22


def _hidden_label() -> MapLabel:
    """A complete but hidden ``LabelConfig`` for objects that carry no label.

    Lines, shapes and containers render no label, but the map schema's
    ``LabelConfig`` requires all of ``show``/``x``/``y``/``size``/``color``/
    ``background`` — a bare ``{"show": False}`` is rejected on save. Emit a full,
    hidden config so the import round-trips through the Maps REST API.
    """
    return {
        "show": False,
        "x": 0,
        "y": 0,
        "size": 11,
        "color": "#000000",
        "background": "transparent",
    }


def _label(p: dict[str, str], *, show_default: bool = True) -> MapLabel:
    raw_bg = p.get("label_background", "transparent")
    # NagVis canvas is light, so default to black; flip only for opaque-dark bg.
    default_color = "#ffffff" if _bg_is_opaque_dark(raw_bg) else "#000000"
    return {
        "show": _bool(p.get("label_show"), show_default),
        "text": _label_text(p.get("label_text")),
        "x": _label_x(p.get("label_x")),
        "y": _label_y(p.get("label_y")),
        "size": _int(p.get("label_size"), 11),
        "color": _color(p.get("label_color"), default_color),
        "background": _color(raw_bg, "transparent"),
        "width": _int(p.get("label_width")) or None,
    }


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------


# Only ``aggr`` is renamed; every other block type carries over verbatim.
_MONITOR_OBJECT_TYPES: dict[str, ObjectType] = {
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
_NON_INHERITED_KEYS = frozenset({"object_id", "name", "template"})

# Global-block keys that configure the map itself (handled by _apply_global)
# and must not be pushed onto every object as a default. backend_id stays
# map-level so an object only gets a connection override where its own block (or
# its template) names one — see the object loop in cfg_to_map.
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
    }
)


# NagVis geographic map sources that become an Maps worldmap (geo) map.
# ``dynmap`` is excluded — it is a dynamic-filter map, not geographic.
_GEO_SOURCES = {"worldmap", "geomap"}
_GEO_DEFAULT_LAT = 51.0
_GEO_DEFAULT_LNG = 10.0
_GEO_DEFAULT_ZOOM = 5


def _parse_latlng(value: str | None) -> tuple[float, float] | None:
    """Parse a NagVis ``worldmap_center`` value (``"lat,lng"``) into floats."""
    if not value:
        return None
    parts = [s.strip() for s in value.split(",")]
    if len(parts) != 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


def _geo_view(p: dict[str, str]) -> WorldmapView:
    """Build an Maps worldmap view from a NagVis worldmap/geomap global block.

    Worldmap objects live in ``etc/worldmap.db`` and geomap hosts in a CSV — both
    are sidecar files the text-only map import can't read, so the UI import
    produces a correctly-framed but empty geo map. The CLI importer
    (tools/cfg_importer.py) fills the markers in from those sidecars.
    """
    lat, lng = _parse_latlng(p.get("worldmap_center")) or (_GEO_DEFAULT_LAT, _GEO_DEFAULT_LNG)
    zoom = p.get("worldmap_zoom") or p.get("geomap_zoom")
    view: WorldmapView = {
        "type": "worldmap",
        "lat": lat,
        "lng": lng,
        "zoom": _int(zoom, _GEO_DEFAULT_ZOOM) if zoom else _GEO_DEFAULT_ZOOM,
    }
    saturate = p.get("worldmap_tiles_saturate")
    if saturate not in (None, ""):
        view["tile_saturate"] = float(max(0, min(100, _int(saturate, 100))))
    return view


def _apply_global(map_cfg: MapPayload, p: dict[str, str]) -> None:
    if "alias" in p:
        map_cfg["alias"] = p["alias"]
    if "map_image" in p:
        map_cfg["background_image"] = p["map_image"]
    if "background_color" in p:
        map_cfg["background_color"] = _color(p["background_color"], "#ffffff")
    # NagVis cfg uses the legacy "backend_id" parameter name on disk; map to our
    # canonical "connection_id" while reading.
    if "backend_id" in p:
        map_cfg["connection_id"] = p["backend_id"]
    if "iconset" in p:
        map_cfg["icon_size"] = ICONSET_SIZE.get(p["iconset"], 22)

    sources = {s.strip().lower() for s in p.get("sources", "").split(",") if s.strip()}
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
        # NagVis default line_color_border = #000000; renders the colored fill
        # over a black outline.
        "line_color_border": _color(p.get("line_color_border"), "#000000"),
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
    _set_explicit_z(payload, p)
    refs: dict[_Axis, _Coord] = {"x": x, "y": y, "x2": x2, "y2": y2}
    # Explicit bend/meeting point (NagVis stored the middle of a 3-coord line).
    if mid_x is not None and mid_y is not None:
        payload["mid_x"] = mid_x.value
        payload["mid_y"] = mid_y.value
        refs["mid_x"] = mid_x
        refs["mid_y"] = mid_y
    return _ImportObject(payload, _pending(refs))


def _apply_weathermap_defaults(obj: MapObject) -> None:
    """Give weathermap lines NagVis' implicit in/out metric defaults.

    NagVis needs no metric configuration: line_label_in/line_label_out default
    to "in"/"out" and are matched against the bound service's perfdata. Maps
    requires an explicit weathermap_metric, so mirror that default — otherwise
    imported weathermap lines have the gradient enabled but no metric to read
    and stay uncolored.
    """
    if not obj.get("line_weather_color"):
        return
    obj.setdefault("weathermap_metric", "in")
    obj.setdefault("weathermap_metric_out", "out")


def _handle_view_type_line(p: dict[str, str], raw_id: str) -> _ImportObject:
    """Service/host block with view_type=line — render as a line.

    Legacy format encodes a line this way; recognising it explicitly avoids
    the icon path treating the comma-separated x/y as broken coords.
    """
    obj = _line_obj_common(p, raw_id)
    if "host_name" in p:
        obj.payload["host_name"] = p["host_name"]
    if "service_description" in p:
        obj.payload["service_description"] = p["service_description"]
    # Legacy: line_label_in/out name the inbound/outbound perfdata fields so
    # the bandwidth labels can render flanking the midpoint.
    if "line_label_in" in p:
        obj.payload["weathermap_metric"] = p["line_label_in"]
    if "line_label_out" in p:
        obj.payload["weathermap_metric_out"] = p["line_label_out"]
    _apply_weathermap_defaults(obj.payload)
    return obj


def _handle_line_block(p: dict[str, str], raw_id: str) -> _ImportObject:
    obj = _line_obj_common(p, raw_id)
    # Stateful line variants (13/14/15) — bind to host/service so live
    # bandwidth and weather-color have data to read from.
    if obj.payload.get("line_perfdata_label", "none") != "none":
        if "host_name" in p:
            obj.payload["host_name"] = p["host_name"]
        if "service_description" in p:
            obj.payload["service_description"] = p["service_description"]
        if "weathermap_metric" in p:
            obj.payload["weathermap_metric"] = p["weathermap_metric"]
        if "weathermap_metric_out" in p:
            obj.payload["weathermap_metric_out"] = p["weathermap_metric_out"]
    _apply_weathermap_defaults(obj.payload)
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
    return _ImportObject(payload, _pending({"x": x, "y": y}))


def _handle_container(p: dict[str, str], raw_id: str) -> _ImportObject:
    """NagVis ``container`` (embeds a URL's content) → Maps ``graph`` iframe.

    Maps has no dedicated container type; the graph object is the structural
    match — an iframe box at x/y with width/height. ``graph_url`` is validated on
    the schema, so the raw NagVis URL is safe to pass through here.
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
    m = re.search(r'<font[^>]*color=["\']([^"\']+)', html, re.IGNORECASE)
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
    elif m := re.search(r'<font[^>]*\bsize=["\']?([1-7])', html, re.IGNORECASE):
        out["size"] = _FONT_SIZE_HTML[m.group(1)]
    if re.search(r"<b\b", html, re.IGNORECASE) or re.search(
        r"font-weight\s*:\s*bold", html, re.IGNORECASE
    ):
        out["weight"] = "bold"
    if m := re.search(_TEXT_ALIGN_RE, html, re.IGNORECASE):
        out["align"] = _TEXT_ALIGNS[m.group(1).lower()]
    return out


def _handle_textbox(p: dict[str, str], raw_id: str) -> _ImportObject:
    raw_text = p.get("text") or None
    html_style: _HtmlStyle = {}
    if raw_text:
        html_style = _extract_html_style(raw_text)
        raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"<[^>]+>", "", raw_text)
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
    label: MapLabel = {
        "show": True,
        "text": raw_text,
        "x": 0,
        "y": 0,
        "size": html_style.get("size", 11),
        "color": _color(html_style.get("color"), "#000000"),
        "background": "transparent",
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
        # NagVis default is transparent; lets lines drawn under the textbox
        # stay visible on the white canvas.
        "textbox_background": _color(p.get("background_color"), "transparent"),
    }
    _set_explicit_z(payload, p)
    if width is not None:
        payload["textbox_width"] = width
    if height is not None:
        payload["textbox_height"] = height
    # NagVis textbox border_color default is #e5e5e5 (light gray); explicit
    # #000000 in cfg renders prominent black, unset stays subtle.
    payload["textbox_border"] = _color(p.get("border_color"), "#e5e5e5")
    return _ImportObject(payload, _pending({"x": tx, "y": ty}))


def _build_display(p: dict[str, str]) -> MapDisplay:
    view_type = p.get("view_type", "icon")
    if view_type == "text":
        return {"mode": "text"}
    if view_type != "gadget":
        return {"mode": "icon"}
    # Legacy default for an unset gadget_url is the speedometer; render as gauge.
    # Unknown values fall back to icon so the object stays visible.
    gadget_url = p.get("gadget_url", "").strip()
    gadget_type = _GADGET_URL_MAP.get(gadget_url)
    if gadget_type is None and gadget_url == "":
        gadget_type = "gauge"
    if gadget_type is None:
        return {"mode": "icon"}
    return {"mode": "gadget", "gadget_type": gadget_type, "gadget_metric": None}


def _apply_type_specific(obj: MapObject, block_type: str, p: dict[str, str]) -> None:
    if block_type == "host":
        obj["host_name"] = p.get("host_name")
        if _bool(p.get("only_hard_states")):
            obj["only_hard_states"] = True
        if _bool(p.get("recognize_services")):
            obj["recognize_services"] = True
    elif block_type == "service":
        obj["host_name"] = p.get("host_name")
        obj["service_description"] = p.get("service_description")
        if _bool(p.get("only_hard_states")):
            obj["only_hard_states"] = True
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


def _handle_monitor_block(block_type: str, p: dict[str, str], raw_id: str) -> _ImportObject:
    """host / service / hostgroup / servicegroup / map / aggr."""
    maps_type = _MONITOR_OBJECT_TYPES[block_type]
    x, y = _parse_coord(p.get("x", "0"), "x"), _parse_coord(p.get("y", "0"), "y")
    payload: MapObject = {
        "id": f"{maps_type}_{raw_id}",
        "type": maps_type,
        "x": x.value,
        "y": y.value,
        "label": _label(p),
        "display": _build_display(p),
        # NagVis .box CSS draws every label with a 1px solid border (#e5e5e5).
        "label_border": _color(p.get("label_border"), "#e5e5e5"),
    }
    _set_explicit_z(payload, p)
    _apply_type_specific(payload, block_type, p)
    if "url" in p:
        payload["url"] = p["url"]
    if "url_target" in p:
        raw_target = p["url_target"]
        payload["url_target"] = "_blank" if raw_target in _FRAMESET_TARGETS else raw_target
    return _ImportObject(payload, _pending({"x": x, "y": y}))


def _handle_object_block(block_type: str, p: dict[str, str], raw_id: str) -> _ImportObject | None:
    if p.get("view_type") == "line":
        return _handle_view_type_line(p, raw_id)
    if block_type == "line":
        return _handle_line_block(p, raw_id)
    if block_type == "shape":
        return _handle_shape(p, raw_id)
    if block_type == "textbox":
        return _handle_textbox(p, raw_id)
    if block_type == "container":
        return _handle_container(p, raw_id)
    return _handle_monitor_block(block_type, p, raw_id)


def cfg_to_map(content: str, map_name: str) -> MapPayload:
    """Convert legacy .cfg text to an Maps map JSON dict."""
    map_cfg: MapPayload = {
        "name": map_name,
        "alias": map_name,
        "connection_id": "live_1",
        "icon_size": 22,
        "rotation_interval": 0,
        "hover_template": None,
        "context_template": None,
        "background_image": None,
        # Map-level defaults required by the Maps map schema (the SPA sets the
        # same on dialog-created maps); NagVis has no equivalent knobs.
        "sort_order": 0,
        "click_action": "link",
        # cfg-imports render with NagVis-classic top-left anchoring + flat look.
        "render_mode": "nagvis_classic",
        # NagVis' global default z is 10 for every object type and is never
        # written per-object; objects without an explicit z inherit this.
        "default_z": 10,
        # NagVis falls back to a white canvas when map_image is missing.
        "background_color": "#ffffff",
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

    # Pre-pass: collect templates and global object-defaults. NagVis resolves
    # each parameter as object > template (``template=name``) > global > built-in
    # default.
    templates: dict[str, dict[str, str]] = {}
    global_props: dict[str, str] = {}
    for block_type, p in blocks:
        if block_type == "template":
            name = p.get("name")
            if name:
                templates[name] = p
        elif block_type == "global":
            global_props = p
    global_defaults = {
        k: v
        for k, v in global_props.items()
        if k not in _NON_INHERITED_KEYS and k not in _GLOBAL_MAP_KEYS
    }

    for block_type, p in blocks:
        if block_type == "global":
            _apply_global(map_cfg, p)
            continue
        if block_type not in _BLOCK_TYPES:
            continue
        counter += 1
        # object_id identifies the object and is never inherited.
        object_id = p.get("object_id")
        raw_id = object_id or str(counter)
        tmpl = {
            k: v
            for k, v in templates.get(p.get("template", ""), {}).items()
            if k not in _NON_INHERITED_KEYS
        }
        effective = {**global_defaults, **tmpl, **p}
        effective.pop("template", None)
        obj = _handle_object_block(block_type, effective, raw_id)
        if obj is not None:
            # ``url_target`` is a required field on every map object; only the
            # monitor handler sets it (and only when the cfg gave a target). Give
            # everything else NagVis' default so the map round-trips on save.
            obj.payload.setdefault("url_target", "_self")
            # NagVis allows backend_id per object so one map can mix monitoring
            # sources; the daemon honours that (it groups the state fetch by
            # connection). Kept raw here and resolved against the configured
            # connections in resolve_connection_ids, like the map-level id.
            if backend := effective.get("backend_id") or effective.get("connection_id"):
                obj.payload["connection_id"] = backend
            obj.ref_id = object_id
            objects.append(obj)

    _resolve_pending_refs(objects)

    if map_cfg["view"]["type"] in ("flow", "worldmap"):
        # Flow auto-populates from topology; worldmap markers come from a sidecar
        # file (worldmap.db / geomap CSV) the text-only import can't read, so the
        # map is framed here and filled by the CLI importer.
        objects = []
    map_cfg["objects"] = [obj.payload for obj in objects]
    return map_cfg


# ---------------------------------------------------------------------------
# GUI endpoint
# ---------------------------------------------------------------------------


def map_name_from_filename(filename: str) -> str:
    """Derive a map name the store and the daemon both accept from the upload."""
    stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(filename).stem)
    return stem[:_MAX_MAP_NAME_LEN] or "imported_map"


def _configured_connection_ids() -> list[str]:
    """Connection ids from the WATO-owned ``maps_connections`` global.

    The import remaps a .cfg's ``backend_id`` to a real local connection like the
    legacy path did. The daemon used to resolve this against its live registry;
    the GUI owns the connection config, so read the configured list here.
    """
    return [cid for cid, _label in connection_choices()]


def resolve_connection_ids(map_cfg: MapPayload, configured: Sequence[str]) -> list[str]:
    """Point the map and its objects at connections that exist here; report what changed.

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

    requested_map_id = map_cfg["connection_id"]
    if requested_map_id not in configured and configured:
        map_cfg["connection_id"] = configured[0]
        warnings.append(
            _(
                "The map's monitoring connection %(requested)r is not configured here. "
                "The map now uses %(used)r."
            )
            % {"requested": requested_map_id, "used": configured[0]}
        )

    inherited = {requested_map_id, map_cfg["connection_id"]}
    dropped: Counter[str] = Counter()
    for obj in map_cfg["objects"]:
        override = obj.get("connection_id")
        if override is None:
            continue
        if override in inherited:
            # Same source as the map — an override would be redundant.
            del obj["connection_id"]
        elif override not in configured:
            del obj["connection_id"]
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


def parse_cfg_upload(filename: str, contents: bytes) -> tuple[MapPayload, list[str]]:
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
    map_cfg = cfg_to_map(
        contents.decode("utf-8", errors="replace"), map_name_from_filename(filename)
    )
    return map_cfg, resolve_connection_ids(map_cfg, _configured_connection_ids())
