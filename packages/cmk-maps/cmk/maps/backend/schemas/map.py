#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Map configuration schemas."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from cmk.maps.backend.schemas.presentation import PresentationView
from cmk.maps.shared.filters import normalize_object_filter
from cmk.maps.shared.map_payload import (
    ClickAction,
    LinePerfdataLabel,
    LineStyle,
    ObjectType,
    RenderMode,
)
from cmk.maps.shared.validators import validate_color, validate_user_url


def _accept_legacy_backend_id(data: object) -> object:
    """Translate the pre-rename ``backend_id`` key to ``connection_id`` on input.

    Older map JSON files (written before the rename) carry ``backend_id``;
    the field name on the model is ``connection_id``. Run as a ``mode='before'``
    validator so the value reaches the canonical field, but never serialises
    back under the legacy name.
    """
    if isinstance(data, dict) and "backend_id" in data and "connection_id" not in data:
        data["connection_id"] = data.pop("backend_id")
    return data


class AggregationInfo(BaseModel):
    """Discovery payload for a Checkmk BI aggregation (used by the editor autocomplete)."""

    id: str
    title: str
    pack_id: str
    # Top-level aggregation function (worst / best / count_ok / call_a_rule
    # / state_of_host / state_of_service / ...). The EditPanel renders this
    # as a read-only chip so the designer doesn't have to crosscheck WATO
    # to know what semantic the aggregation has.
    function: str | None = None


class AggregationNode(BaseModel):
    """One node in a BI aggregation hierarchy (mirrors cmk.gui.nodevis output).

    ``node_type`` is ``"bi_aggregator"`` for rule nodes and ``"bi_leaf"`` for
    host/service leaves — same identifiers Checkmk uses, so frontend rendering
    can later be merged with cmk's node visualization. ``state`` is the BI
    integer state (0=OK, 1=WARN, 2=CRIT, 3=UNKNOWN).
    """

    name: str
    node_type: Literal["bi_aggregator", "bi_leaf"]
    state: int
    in_downtime: bool = False
    acknowledged: bool = False
    host_name: str | None = None
    service_description: str | None = None
    # Plugin output of the node's compute result (leaf check output for
    # bi_leaf nodes). Lets the drawer surface the worst leaf's output
    # without a second per-leaf fetch.
    output: str = ""
    children: list[AggregationNode] = []


def _migrate_weathermap(data: object) -> object:
    """Translate legacy ``line_style: weathermap`` to the new orthogonal model.

    The old monolithic style bundled three orthogonal aspects (bidirectional
    shape, bandwidth labels, utilization gradient). Stored maps using it
    are rewritten transparently during validation so old JSON keeps loading.
    """
    if isinstance(data, dict) and data.get("line_style") == "weathermap":
        migrated = {**data, "line_style": "arrow_inward"}
        migrated.setdefault("line_perfdata_label", "bandwidth")
        migrated.setdefault("line_weather_color", True)
        return migrated
    return data


class LabelConfig(BaseModel):
    show: bool = True
    text: str | None = None
    x: int = 0
    y: int = 0
    size: int = 11
    color: str = "#ffffff"
    background: str = "transparent"
    # NagVis label_width — fixed pixel width that wraps long labels.
    width: int | None = None
    weight: Literal["normal", "bold"] | None = None
    align: Literal["left", "right", "center", "justify"] | None = None

    @field_validator("color", "background")
    @classmethod
    def _validate_label_colors(cls, v: str) -> str:
        return validate_color(v) or v


class DisplayConfig(BaseModel):
    mode: Literal["icon", "text", "gadget"] = "icon"
    image: str | None = None
    image_size: int | None = None
    gadget_type: Literal["gauge", "bar", "trafficlight", "value"] | None = None
    gadget_metric: str | None = None


class StaticView(BaseModel):
    type: Literal["static"] = "static"
    problems_only: bool = False


class WorldmapView(BaseModel):
    type: Literal["worldmap"] = "worldmap"
    lat: float = 51.0
    lng: float = 10.0
    zoom: int = 5
    # Optional override for the Leaflet tile-URL template. Use ``{s}`` for
    # subdomain, ``{z}/{x}/{y}`` for tile coords. When omitted, the frontend
    # fetches tiles directly from OpenStreetMap; set this to point at an
    # internal or caching tile server (e.g. behind a bandwidth-limited network).
    tile_url: str | None = None
    # CSS saturate() filter percent: 0 = greyscale, 100 = unchanged.
    tile_saturate: float | None = Field(default=None, ge=0, le=100)
    # Automap source: when set, the backend dynamically populates the map
    # with hosts that carry maps_lat/maps_lng labels (or legacy LAT/LONG
    # custom variables) from the configured connection. Persisted objects
    # remain visible on top of the auto-discovered ones.
    auto_source: Literal["all_hosts", "hostgroup", "servicegroup"] | None = None
    auto_filter_value: str = ""
    problems_only: bool = False

    @field_validator("tile_url")
    @classmethod
    def _validate_tile_url(cls, v: str | None) -> str | None:
        # Lands in Leaflet's <img src> — same scheme allowlist as object URLs.
        return validate_user_url(v)


class RadarView(BaseModel):
    type: Literal["radar"] = "radar"
    filter: Literal["hostgroup", "servicegroup", "all_hosts", "all_services"] = "hostgroup"
    filter_value: str = ""
    problems_only: bool = False


class FlowNodePosition(BaseModel):
    x: float
    y: float


class FlowView(BaseModel):
    type: Literal["flow"] = "flow"
    root: str | None = None
    # -1 = unlimited; None defaults to unlimited downward / 0 upward (NagVis automap defaults).
    child_layers: int | None = Field(default=None, ge=-1, le=20)
    parent_layers: int | None = Field(default=None, ge=-1, le=20)
    # Per-map overrides for the global flow_map_* limits. None = use the
    # global default from settings.
    top_affected_hosts: int | None = Field(default=None, ge=0, le=1000)
    max_services_per_host: int | None = Field(default=None, ge=0, le=500)
    # Pinned host positions from operator drags. Key is the host name; missing
    # hosts fall back to the force-simulation layout. Service-node positions
    # are derived from their host and not persisted.
    positions: dict[str, FlowNodePosition] = {}
    # Service-node layout chosen by the operator. None = use UI default.
    service_layout: Literal["off", "donut", "fan", "orbit", "row"] | None = None
    problems_only: bool = False


class FolderTreeView(BaseModel):
    type: Literal["foldertree"] = "foldertree"
    # Stable WATO folder ``__id`` (preferred, survives rename/move) or path slug
    # ("" = root / all folders).
    root_folder: str = ""
    # Which presentation the map opens in (operator-chosen, saved per map).
    # Defaults to the treemap — the glanceable status surface; list is secondary.
    default_view: Literal["list", "map"] = "map"
    default_expand_depth: int = Field(default=1, ge=0, le=20)
    show_services: bool = False
    show_empty_folders: bool = True
    problems_only: bool = False
    # What counts as a "problem" for the problems_only filter. On typical
    # sites almost every host carries some WARNING service, so "any" barely
    # filters; "critical" narrows to CRITICAL/DOWN/UNREACHABLE.
    problems_severity: Literal["any", "critical"] = "any"
    only_hard_states: bool = False
    # Distributed monitoring: scope to these site ids; empty = all sites.
    sites: list[str] = []


MapView = Annotated[
    StaticView | WorldmapView | RadarView | FlowView | FolderTreeView | PresentationView,
    Field(discriminator="type"),
]


def view_element_count(view: MapView) -> int:
    """Object count for a map's list/read payload.

    Presentation maps keep ``MapConfig.objects`` empty and carry their
    content as ``view.elements`` instead, so count those for them.
    """
    if isinstance(view, PresentationView):
        return len(view.elements)
    return 0


class MapElement(BaseModel):
    id: str
    type: ObjectType
    # Per-object connection override. ``None`` means "inherit the map's
    # connection_id" — the common case. Setting this lets a single map mix
    # objects from multiple monitoring backends, the way NagVis allows
    # ``backend_id`` per object.
    connection_id: str | None = None
    x: int | float = 0
    y: int | float = 0
    lat: float | None = None
    lng: float | None = None
    # ``None`` means "inherit the map's ``default_z``" — NagVis stores no z on
    # objects that use the global default, so imported objects stay unset and
    # the renderer resolves ``z ?? map.default_z``.
    z: int | None = None
    host_name: str | None = None
    service_description: str | None = None
    group_name: str | None = None
    map_name: str | None = None
    image_src: str | None = None
    x2: int | float | None = None
    y2: int | float | None = None
    lat2: float | None = None
    lng2: float | None = None
    # Optional line bend/meeting point. ``None`` → renderer uses the geometric
    # midpoint of the two endpoints (the previous fixed behavior). A set value
    # mirrors NagVis' explicit middle coordinate on two-segment lines.
    mid_x: int | float | None = None
    mid_y: int | float | None = None
    # Line endpoint bindings: when set, the start/end follows the referenced
    # object's position instead of a fixed coordinate (sticky connectors).
    start_ref: str | None = None
    end_ref: str | None = None
    line_style: LineStyle | None = None
    # Stroke width in pixels. None → renderer's per-style default.
    line_width: int | None = Field(default=None, ge=1, le=20)
    # Which perfdata label to draw at the line midpoint (none/percent/bandwidth/both).
    line_perfdata_label: LinePerfdataLabel = "none"
    # Color the line by inbound/outbound utilization gradient instead of state color.
    line_weather_color: bool = False
    # Inbound metric (rendered left of the midpoint).
    weathermap_metric: str | None = None
    # Outbound metric (rendered right of the midpoint).
    weathermap_metric_out: str | None = None
    cmk_label_name: str | None = None
    cmk_label_value: str | None = None
    cmk_label_target: Literal["hosts", "services"] | None = None
    aggregation_id: str | None = None
    # Dyngroup: arbitrary Livestatus filter producing a set of hosts/services.
    object_types: Literal["host", "service"] | None = None
    object_filter: str | None = None
    # Set ⇒ this dyngroup is a geo "bundle": worst-state folds host + service
    # severities, and the worldmap automap suppresses the member hosts' markers.
    bundle_kind: Literal["static", "location"] | None = None
    bundle_hosts: list[str] | None = None
    # None ⇒ exact coordinate match (5 decimals ≈ 1 m).
    bundle_precision: int | None = Field(default=None, ge=0, le=8)
    # 0 = root only, hard cap 10 levels — see backend.app.services.state_service.
    expand_depth: int = Field(default=0, ge=0, le=10)
    only_hard_states: bool = False
    recognize_services: bool = False
    exclude_members: str | None = None
    exclude_member_states: str | None = None
    label: LabelConfig | None = LabelConfig()
    display: DisplayConfig | None = DisplayConfig()
    label_border: str | None = None
    label_maxlen: int | None = None
    textbox_background: str | None = None
    textbox_border: str | None = None
    textbox_width: int | None = None
    textbox_height: int | None = None
    graph_url: str | None = None
    graph_embed_type: Literal["img", "iframe"] = "img"
    graph_width: int = 400
    graph_height: int = 200
    graph_refresh_interval: int = 0
    graph_metric: list[str] | None = None
    graph_id: str | None = None
    graph_time_window: int | None = None  # minutes; None = all stored history

    @field_validator("graph_metric", mode="before")
    @classmethod
    def _coerce_graph_metric(cls, v: object) -> list[str] | None:
        # Backward compat: old saved configs may have a plain string value
        if isinstance(v, str):
            return [v] if v else None
        if v is None:
            return None
        if isinstance(v, list):
            return [s for s in v if isinstance(s, str)]
        return None

    @field_validator("url", "hover_url", "graph_url")
    @classmethod
    def _validate_urls(cls, v: str | None) -> str | None:
        return validate_user_url(v)

    @field_validator(
        "line_color", "line_color_border", "label_border", "textbox_background", "textbox_border"
    )
    @classmethod
    def _validate_colors(cls, v: str | None) -> str | None:
        return validate_color(v)

    @field_validator("object_filter")
    @classmethod
    def _validate_object_filter(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        return normalize_object_filter(v)

    @model_validator(mode="before")
    @classmethod
    def _legacy_weathermap(cls, data: object) -> object:
        return _migrate_weathermap(data)

    line_color: str | None = None
    line_color_border: str | None = None
    url: str | None = None
    url_target: str = "_blank"
    hover_url: str | None = None
    hover_template: str | None = None
    context_template: str | None = None


class MapConfig(BaseModel):
    _migrate_legacy_keys = model_validator(mode="before")(_accept_legacy_backend_id)

    # Constrained like MapRead.name: the name keys the in-memory cache and the
    # on-disk path, so an unvalidated value would allow cache poisoning / path
    # traversal via the (auth-only) register endpoint. Matches the GUI's
    # is_valid_map_name so a GUI-saved map always round-trips.
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    alias: str = ""
    readonly: bool = False
    show_in_lists: bool = True
    connection_id: str = "live_1"
    icon_size: int | None = None
    rotation_interval: int = 0
    sort_order: int = 0
    click_action: ClickAction = "link"
    hover_template: str | None = None
    context_template: str | None = None
    background_image: str | None = None
    background_color: str | None = None
    # Default keeps existing maps on the Maps renderer; "nagvis_classic"
    # opts an imported map into top-left anchoring + flat styling.
    render_mode: RenderMode = "default"
    # Map-wide fallback z for objects that carry no explicit ``z`` (mirrors
    # NagVis' global default). Default 1 preserves the historic per-object
    # default; the cfg importer writes 10 to match NagVis exactly.
    default_z: int = 1
    # Monotonically incremented per persisted change. Compared against the
    # client's ``If-Match`` header on update; mismatch returns 409 Conflict so
    # two operators editing the same map don't silently lose changes.
    version: int = 0
    # Locks the percent-positioning divisor: without a persisted size the reload
    # re-derives a larger one from padded extents, re-anchoring every object when
    # one was dragged to an edge. None on legacy maps → derived from extents.
    canvas_width: int | None = None
    canvas_height: int | None = None
    view: MapView = StaticView()
    # Capped like the bulk-op name lists: ``register`` is authentication-only, so
    # an unbounded object list would let one caller pin large payloads in the
    # streaming cache. 5000 is far above any hand-curated map yet bounds a
    # pathological payload.
    objects: list[MapElement] = Field(default=[], max_length=5000)


class MapCreate(BaseModel):
    _migrate_legacy_keys = model_validator(mode="before")(_accept_legacy_backend_id)

    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    alias: str = ""
    background_image: str | None = None
    background_color: str | None = None
    icon_size: int | None = None
    connection_id: str = "live_1"
    view: MapView = StaticView()
    render_mode: RenderMode = "default"
    default_z: int = 1


class MapUpdate(BaseModel):
    _migrate_legacy_keys = model_validator(mode="before")(_accept_legacy_backend_id)

    alias: str | None = None
    background_image: str | None = None
    background_color: str | None = None
    icon_size: int | None = None
    connection_id: str | None = None
    view: MapView | None = None
    sort_order: int | None = None
    click_action: ClickAction | None = None
    hover_template: str | None = None
    context_template: str | None = None
    rotation_interval: int | None = None
    show_in_lists: bool | None = None
    render_mode: RenderMode | None = None
    default_z: int | None = None
    canvas_width: int | None = None
    canvas_height: int | None = None


class MapOrderItem(BaseModel):
    name: str
    sort_order: int


class MapRead(BaseModel):
    _migrate_legacy_keys = model_validator(mode="before")(_accept_legacy_backend_id)

    name: str
    alias: str
    background_image: str | None
    background_color: str | None = None
    icon_size: int | None
    connection_id: str
    view_type: str
    view: MapView
    object_count: int
    rotation_interval: int
    version: int = 0
    sort_order: int = 0
    click_action: ClickAction = "link"
    readonly: bool = False
    show_in_lists: bool = True
    hover_template: str | None = None
    context_template: str | None = None
    render_mode: RenderMode = "default"
    default_z: int = 1
    # Per-user capability stamped by the list endpoint: whether the requesting
    # user may edit this map (admins, or non-admins with edit permission).
    can_edit: bool = False


class MapElementUpdate(BaseModel):
    """Allowed fields for a partial object update — id and type are immutable."""

    connection_id: str | None = None
    x: int | float | None = None
    y: int | float | None = None
    lat: float | None = None
    lng: float | None = None
    z: int | None = None
    host_name: str | None = None
    service_description: str | None = None
    group_name: str | None = None
    map_name: str | None = None
    image_src: str | None = None
    x2: int | float | None = None
    y2: int | float | None = None
    lat2: float | None = None
    lng2: float | None = None
    mid_x: int | float | None = None
    mid_y: int | float | None = None
    start_ref: str | None = None
    end_ref: str | None = None
    line_style: LineStyle | None = None
    line_width: int | None = Field(default=None, ge=1, le=20)
    line_perfdata_label: LinePerfdataLabel | None = None
    line_weather_color: bool | None = None
    weathermap_metric: str | None = None
    weathermap_metric_out: str | None = None
    cmk_label_name: str | None = None
    cmk_label_value: str | None = None
    cmk_label_target: Literal["hosts", "services"] | None = None
    aggregation_id: str | None = None
    object_types: Literal["host", "service"] | None = None
    object_filter: str | None = None
    bundle_kind: Literal["static", "location"] | None = None
    bundle_hosts: list[str] | None = None
    bundle_precision: int | None = Field(default=None, ge=0, le=8)
    expand_depth: int | None = Field(default=None, ge=0, le=10)
    only_hard_states: bool | None = None
    recognize_services: bool | None = None
    exclude_members: str | None = None
    exclude_member_states: str | None = None
    label: LabelConfig | None = None
    display: DisplayConfig | None = None
    label_border: str | None = None
    label_maxlen: int | None = None
    textbox_background: str | None = None
    textbox_border: str | None = None
    textbox_width: int | None = None
    textbox_height: int | None = None
    graph_url: str | None = None
    graph_embed_type: Literal["img", "iframe"] | None = None
    graph_width: int | None = None
    graph_height: int | None = None
    graph_refresh_interval: int | None = None
    graph_metric: list[str] | None = None
    graph_id: str | None = None
    graph_time_window: int | None = None
    line_color: str | None = None
    line_color_border: str | None = None
    url: str | None = None
    url_target: str | None = None
    hover_url: str | None = None
    hover_template: str | None = None
    context_template: str | None = None

    @field_validator("url", "hover_url", "graph_url")
    @classmethod
    def _validate_urls(cls, v: str | None) -> str | None:
        return validate_user_url(v)

    @field_validator(
        "line_color", "line_color_border", "label_border", "textbox_background", "textbox_border"
    )
    @classmethod
    def _validate_colors(cls, v: str | None) -> str | None:
        return validate_color(v)

    @field_validator("object_filter")
    @classmethod
    def _validate_object_filter(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        return normalize_object_filter(v)

    @model_validator(mode="before")
    @classmethod
    def _legacy_weathermap(cls, data: object) -> object:
        return _migrate_weathermap(data)


class MapClone(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    alias: str | None = None


class MapPermissionsRead(BaseModel):
    """Which roles have view/edit access to a specific map (by name, not wildcard)."""

    view: list[str]
    edit: list[str]


_MapNameStr = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")]


class MapBulkDelete(BaseModel):
    names: Annotated[list[_MapNameStr], Field(min_length=1, max_length=500)]


class MapBulkDeleteFailure(BaseModel):
    name: str
    reason: str


class MapBulkDeleteResult(BaseModel):
    deleted: list[str]
    failed: list[MapBulkDeleteFailure]


class MapBulkEdit(BaseModel):
    names: Annotated[list[_MapNameStr], Field(min_length=1, max_length=500)]
    # Untyped dict on purpose: the API layer first runs the FormSpec wire
    # conversions (rotation cascading → int, click_action bool → literal)
    # and then validates the resulting subset against ``MapUpdate``.
    updates: dict[str, object]


class MapBulkEditFailure(BaseModel):
    name: str
    reason: str


class MapBulkEditResult(BaseModel):
    updated: list[str]
    failed: list[MapBulkEditFailure]


class MapBulkExport(BaseModel):
    names: Annotated[list[_MapNameStr], Field(min_length=1, max_length=500)]
