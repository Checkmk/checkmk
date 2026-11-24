#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Map configuration schemas."""

from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    field_validator,
    model_validator,
)

from cmk.maps.backend.schemas.presentation import PresentationView
from cmk.maps.shared.filters import (
    bound_type_of,
    check_host_member_patterns,
    normalize_object_filter,
    optional_member_pattern,
)
from cmk.maps.shared.geo import LAT_LIMIT, LNG_LIMIT, MAX_ZOOM
from cmk.maps.shared.map_compat import (
    accept_legacy_backend_id,
    coerce_graph_metric,
    migrate_weathermap,
)
from cmk.maps.shared.map_name import MAP_NAME_MAX_LENGTH, MAP_NAME_PATTERN
from cmk.maps.shared.map_payload import (
    BackgroundPosition,
    BackgroundStyle,
    BUNDLE_HOSTS_MAX,
    BUNDLE_PRECISION_MAX,
    ClickAction,
    FLOW_LAYERS_MAX,
    FLOW_LAYERS_MIN,
    FLOW_POSITIONS_MAX,
    FLOW_SERVICES_PER_HOST_MAX,
    FLOW_TOP_AFFECTED_HOSTS_MAX,
    FOLDER_EXPAND_DEPTH_MAX,
    GRID_FIELD_DEFAULTS,
    GRID_ID_PATTERN,
    GRID_OFFSET_MAX,
    GRID_PER_ROW_MAX,
    GridOrder,
    GridSort,
    LINE_WIDTH_MAX,
    LINE_WIDTH_MIN,
    LinePerfdataLabel,
    LineStyle,
    MAP_BUNDLE_HOSTS_MAX,
    MAP_OBJECTS_MAX,
    MonitoredObjectType,
    OBJECT_EXPAND_DEPTH_MAX,
    ObjectType,
    RenderMode,
)
from cmk.maps.shared.validators import (
    check_grid,
    check_grid_binding,
    check_grids,
    coerce_asset_ref,
    coerce_url_target,
    ConnectionId,
    FiniteFloat,
    MAX_ROTATION_POOLS,
    validate_color,
    validate_graph_url,
    validate_host_name,
    validate_rotation_pool,
    validate_tile_url,
    validate_user_url,
)

# Uploaded icon / background references are bare filenames the SPA expands into an
# asset URL; drop anything that could climb out of the asset directory.
_AssetRef = Annotated[str | None, BeforeValidator(coerce_asset_ref)]
_RotationPool = Annotated[str, AfterValidator(validate_rotation_pool)]
_HostName = Annotated[str, AfterValidator(validate_host_name)]


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
    # How a text box aligns its text. An object's label in the NagVis-compatible
    # renderer starts at ``x`` when left-aligned and is centered on it otherwise.
    align: Literal["left", "right", "center", "justify"] | None = None

    @field_validator("color", "background")
    @classmethod
    def _validate_label_colors(cls, v: str) -> str:
        return validate_color(v) or v


class DisplayConfig(BaseModel):
    mode: Literal["icon", "text", "gadget"] = "icon"
    image: _AssetRef = None
    image_size: int | None = None
    gadget_type: Literal["gauge", "bar", "trafficlight", "value"] | None = None
    gadget_metric: str | None = None


class StaticView(BaseModel):
    type: Literal["static"] = "static"
    problems_only: bool = False


class GeoView(BaseModel):
    type: Literal["geo"] = "geo"
    # Out of these bounds the map opens on nothing.
    lat: FiniteFloat = Field(default=51.0, ge=-LAT_LIMIT, le=LAT_LIMIT)
    lng: FiniteFloat = Field(default=10.0, ge=-LNG_LIMIT, le=LNG_LIMIT)
    zoom: int = Field(default=5, ge=0, le=MAX_ZOOM)
    # Optional override for the Leaflet tile-URL template. Use ``{s}`` for
    # subdomain, ``{z}/{x}/{y}`` for tile coords. When omitted, the frontend
    # fetches tiles directly from OpenStreetMap; set this to point at an
    # internal or caching tile server (e.g. behind a bandwidth-limited network).
    tile_url: str | None = None
    # CSS saturate() filter percent: 0 = greyscale, 100 = unchanged.
    tile_saturate: FiniteFloat | None = Field(default=None, ge=0, le=100)
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
        return validate_tile_url(v)


class RadarView(BaseModel):
    type: Literal["radar"] = "radar"
    filter: Literal["hostgroup", "servicegroup", "all_hosts", "all_services"] = "hostgroup"
    filter_value: str = ""
    problems_only: bool = False


class FlowNodePosition(BaseModel):
    x: FiniteFloat
    y: FiniteFloat


class FlowView(BaseModel):
    type: Literal["flow"] = "flow"
    root: str | None = None
    # -1 = unlimited; None defaults to unlimited downward / 0 upward (NagVis automap defaults).
    child_layers: int | None = Field(default=None, ge=FLOW_LAYERS_MIN, le=FLOW_LAYERS_MAX)
    parent_layers: int | None = Field(default=None, ge=FLOW_LAYERS_MIN, le=FLOW_LAYERS_MAX)
    # Per-map overrides for the global flow_map_* limits. None = use the
    # global default from settings.
    top_affected_hosts: int | None = Field(default=None, ge=0, le=FLOW_TOP_AFFECTED_HOSTS_MAX)
    max_services_per_host: int | None = Field(default=None, ge=0, le=FLOW_SERVICES_PER_HOST_MAX)
    # Pinned host positions from operator drags. Key is the host name; missing
    # hosts fall back to the force-simulation layout. Service-node positions
    # are derived from their host and not persisted.
    positions: dict[str, FlowNodePosition] = Field(default={}, max_length=FLOW_POSITIONS_MAX)
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
    default_expand_depth: int = Field(default=1, ge=0, le=FOLDER_EXPAND_DEPTH_MAX)
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
    StaticView | GeoView | RadarView | FlowView | FolderTreeView | PresentationView,
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
    connection_id: ConnectionId | None = None
    x: int | FiniteFloat = 0
    y: int | FiniteFloat = 0
    lat: FiniteFloat | None = None
    lng: FiniteFloat | None = None
    # ``None`` means "inherit the map's ``default_z``" — NagVis stores no z on
    # objects that use the global default, so imported objects stay unset and
    # the renderer resolves ``z ?? map.default_z``.
    z: int | None = None
    host_name: str | None = None
    service_description: str | None = None
    group_name: str | None = None
    map_name: str | None = None
    image_src: _AssetRef = None
    x2: int | FiniteFloat | None = None
    y2: int | FiniteFloat | None = None
    lat2: FiniteFloat | None = None
    lng2: FiniteFloat | None = None
    # Optional line bend/meeting point. ``None`` → renderer uses the geometric
    # midpoint of the two endpoints (the previous fixed behavior). A set value
    # mirrors NagVis' explicit middle coordinate on two-segment lines.
    mid_x: int | FiniteFloat | None = None
    mid_y: int | FiniteFloat | None = None
    # Line endpoint bindings: when set, the start/end follows the referenced
    # object's position instead of a fixed coordinate (sticky connectors).
    start_ref: str | None = None
    end_ref: str | None = None
    line_style: LineStyle | None = None
    # Stroke width in pixels. None → renderer's per-style default.
    line_width: int | None = Field(default=None, ge=LINE_WIDTH_MIN, le=LINE_WIDTH_MAX)
    # Which perfdata label to draw at the line midpoint (none/percent/bandwidth/both).
    line_perfdata_label: LinePerfdataLabel = "none"
    # Color the line by inbound/outbound utilization gradient instead of state color.
    line_weather_color: bool = False
    # What the line shows the state of. ``None`` → a service when one is bound,
    # else the host.
    line_object_type: MonitoredObjectType | None = None
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
    # severities, and the geo map automap suppresses the member hosts' markers.
    bundle_kind: Literal["static", "location"] | None = None
    bundle_hosts: list[_HostName] | None = Field(default=None, max_length=BUNDLE_HOSTS_MAX)
    # None ⇒ exact coordinate match (5 decimals ≈ 1 m).
    bundle_precision: int | None = Field(default=None, ge=0, le=BUNDLE_PRECISION_MAX)
    # 0 = root only, hard cap 10 levels — see backend.app.services.state_service.
    expand_depth: int = Field(default=0, ge=0, le=OBJECT_EXPAND_DEPTH_MAX)
    only_hard_states: bool = False
    recognize_services: bool = False
    exclude_members: str | None = None
    exclude_member_states: str | None = None
    # A grid lays out the hosts or services its filter matches, or all of them,
    # from x/y, as a NagVis dynmap; its label, display and state options apply
    # to them. The defaults are NagVis' ``dynmap_*`` defaults.
    grid_per_row: int = Field(
        default=GRID_FIELD_DEFAULTS["grid_per_row"], ge=1, le=GRID_PER_ROW_MAX
    )
    grid_offset_x: int = Field(
        default=GRID_FIELD_DEFAULTS["grid_offset_x"], ge=0, le=GRID_OFFSET_MAX
    )
    grid_offset_y: int = Field(
        default=GRID_FIELD_DEFAULTS["grid_offset_y"], ge=0, le=GRID_OFFSET_MAX
    )
    grid_sort: GridSort = GRID_FIELD_DEFAULTS["grid_sort"]
    grid_order: GridOrder = GRID_FIELD_DEFAULTS["grid_order"]
    # A host or service pinned out of a grid; that grid leaves it out.
    grid_id: str | None = Field(default=None, pattern=GRID_ID_PATTERN)
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
    graph_metric: Annotated[list[str] | None, BeforeValidator(coerce_graph_metric)] = None
    graph_id: str | None = None
    graph_time_window: int | None = None  # minutes; None = all stored history

    @field_validator("url", "hover_url")
    @classmethod
    def _validate_urls(cls, v: str | None) -> str | None:
        return validate_user_url(v)

    @field_validator("graph_url")
    @classmethod
    def _validate_graph_url(cls, v: str | None) -> str | None:
        return validate_graph_url(v)

    @field_validator("url_target", mode="before")
    @classmethod
    def _coerce_url_target(cls, v: object) -> object:
        return coerce_url_target(v)

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

    @field_validator("exclude_members", "exclude_member_states")
    @classmethod
    def _validate_member_patterns(cls, v: str | None) -> str | None:
        return optional_member_pattern(v)

    _migrate_weathermap = model_validator(mode="before")(migrate_weathermap)

    @model_validator(mode="after")
    def _host_takes_no_service_pattern(self) -> Self:
        bound = bound_type_of(
            self.type, self.line_object_type, self.service_description, self.object_types
        )
        check_host_member_patterns(bound, self.exclude_members, self.exclude_member_states)
        check_grid(self.type, self.id)
        check_grid_binding(
            self.type,
            self.object_types,
            grid_id=self.grid_id,
            recognize_services=self.recognize_services,
            member_patterns=(self.exclude_members, self.exclude_member_states),
        )
        return self

    line_color: str | None = None
    line_color_border: str | None = None
    url: str | None = None
    url_target: str = "_blank"
    hover_url: str | None = None
    hover_template: str | None = None
    context_template: str | None = None


class MapConfig(BaseModel):
    _migrate_legacy_keys = model_validator(mode="before")(accept_legacy_backend_id)

    # The name keys the in-memory cache and the on-disk path, so an unvalidated
    # value would allow cache poisoning / path traversal via the (auth-only)
    # register endpoint. Matches the GUI's is_valid_map_name so a GUI-saved map
    # always round-trips.
    name: str = Field(..., min_length=1, max_length=MAP_NAME_MAX_LENGTH, pattern=MAP_NAME_PATTERN)
    alias: str = ""
    connection_id: ConnectionId = "live_1"
    icon_size: int | None = None
    rotation_interval: int = 0
    rotation_pools: list[_RotationPool] = Field(default_factory=list, max_length=MAX_ROTATION_POOLS)
    sort_order: int = 0
    click_action: ClickAction = "link"
    hover_template: str | None = None
    context_template: str | None = None
    background_image: _AssetRef = None
    background_color: str | None = None
    # How the image covers the map, in map coordinates; "nagvis_classic"
    # ignores both and always draws it at its own size.
    background_style: BackgroundStyle = "single"
    background_position: BackgroundPosition = "top_left"
    # Default keeps existing maps on the Maps renderer; "nagvis_classic"
    # opts an imported map into NagVis' geometry (top-left anchoring, labels at
    # their own offset, the background at its own size).
    render_mode: RenderMode = "default"
    # Map-wide fallback z for objects that carry no explicit ``z`` (mirrors
    # NagVis' global default). Default 1 preserves the historic per-object
    # default; the cfg importer writes 10 to match NagVis exactly.
    default_z: int = 1
    # Set by the GUI on every save, rising, so ``register`` refuses a config
    # signed before the one it holds.
    version: int = 0
    # Locks the percent-positioning divisor: without a persisted size the reload
    # re-derives a larger one from padded extents, re-anchoring every object when
    # one was dragged to an edge. None on legacy maps → derived from extents.
    canvas_width: int | None = None
    canvas_height: int | None = None
    view: MapView = StaticView()
    objects: list[MapElement] = Field(default=[], max_length=MAP_OBJECTS_MAX)

    @model_validator(mode="after")
    def _bundle_hosts_in_total(self) -> Self:
        if sum(len(o.bundle_hosts or ()) for o in self.objects) > MAP_BUNDLE_HOSTS_MAX:
            raise ValueError(f"A map's bundles take at most {MAP_BUNDLE_HOSTS_MAX} hosts in all")
        return self

    @field_validator("background_color")
    @classmethod
    def _validate_background_color(cls, v: str | None) -> str | None:
        return validate_color(v)

    @model_validator(mode="after")
    def _check_grids(self) -> Self:
        check_grids(self.view.type, (o.type for o in self.objects))
        return self


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
    image_src: _AssetRef = None
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
    line_object_type: MonitoredObjectType | None = None
    weathermap_metric: str | None = None
    weathermap_metric_out: str | None = None
    cmk_label_name: str | None = None
    cmk_label_value: str | None = None
    cmk_label_target: Literal["hosts", "services"] | None = None
    aggregation_id: str | None = None
    object_types: Literal["host", "service"] | None = None
    object_filter: str | None = None
    bundle_kind: Literal["static", "location"] | None = None
    bundle_hosts: list[_HostName] | None = Field(default=None, max_length=BUNDLE_HOSTS_MAX)
    bundle_precision: int | None = Field(default=None, ge=0, le=BUNDLE_PRECISION_MAX)
    expand_depth: int | None = Field(default=None, ge=0, le=OBJECT_EXPAND_DEPTH_MAX)
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

    @field_validator("url", "hover_url")
    @classmethod
    def _validate_urls(cls, v: str | None) -> str | None:
        return validate_user_url(v)

    @field_validator("graph_url")
    @classmethod
    def _validate_graph_url(cls, v: str | None) -> str | None:
        return validate_graph_url(v)

    @field_validator("url_target", mode="before")
    @classmethod
    def _coerce_url_target(cls, v: object) -> object:
        return coerce_url_target(v)

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

    @field_validator("exclude_members", "exclude_member_states")
    @classmethod
    def _validate_member_patterns(cls, v: str | None) -> str | None:
        return optional_member_pattern(v)

    _migrate_weathermap = model_validator(mode="before")(migrate_weathermap)
