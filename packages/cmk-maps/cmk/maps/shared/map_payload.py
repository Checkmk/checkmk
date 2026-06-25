#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A map's vocabulary, and its flat wire shape as a plain mapping.

The ``Literal`` aliases below are the one definition of the map vocabulary:
the daemon's pydantic model (``cmk.maps.backend.schemas``) and the REST mirror
(``cmk.maps.rest_api.models.map``) both import them from here.

The ``TypedDict``s serve the GUI-side producers — the NagVis ``.cfg`` importer
and the built-in maps — which build a map as a plain mapping and used to pass it
around as ``dict[str, object]``. They cannot use the daemon's pydantic model
directly: ``cmk.maps.gui`` may not import ``cmk.maps.backend``, and the REST
mirror is out of reach too because ``cmk.maps.rest_api`` depends on
``cmk.maps.gui``, not the other way round. (The schemas themselves are
dependency-free pydantic, so promoting them to a layer all three may import
would remove this mapping entirely — a bigger move than an initial release
warrants.)

They are deliberately a subset: only what those producers actually write.
``test_map_payload_contract`` pins the key names, which keys are mandatory, and
every ``Literal`` domain against the daemon model, so a rename on either side
fails the build instead of silently producing a map the daemon rejects. Value
types and the daemon's numeric constraints are not pinned — a producer that can
emit an out-of-range number has to clamp it itself.
"""

from typing import Literal, NotRequired, TypedDict

# Stable wire tokens — kept in English, never localised.
ObjectType = Literal[
    "host",
    "service",
    "hostgroup",
    "servicegroup",
    "dyngroup",
    "map",
    "image",
    "line",
    "textbox",
    "cmk_label",
    "graph",
    "aggregation",
]

LineStyle = Literal[
    "plain",
    "arrow_end",
    "arrow_start",
    "arrow_both",
    "arrow_inward",
    "dashed",
]

LinePerfdataLabel = Literal["none", "percent", "bandwidth", "both"]

DisplayMode = Literal["icon", "text", "gadget"]

GadgetType = Literal["gauge", "bar", "trafficlight", "value"]

LabelWeight = Literal["normal", "bold"]

LabelAlign = Literal["left", "right", "center", "justify"]

ClickAction = Literal["link", "none"]

RenderMode = Literal["default", "nagvis_classic"]


class MapLabel(TypedDict):
    """A map object's label. The daemon rejects a partial one, so all of
    ``show``/``x``/``y``/``size``/``color``/``background`` are required here."""

    show: bool
    x: int
    y: int
    size: int
    color: str
    background: str
    text: NotRequired[str | None]
    width: NotRequired[int | None]
    weight: NotRequired[LabelWeight]
    align: NotRequired[LabelAlign]


class MapDisplay(TypedDict):
    mode: DisplayMode
    gadget_type: NotRequired[GadgetType]
    gadget_metric: NotRequired[str | None]


MapViewType = Literal[
    "static",
    "worldmap",
    "radar",
    "flow",
    "foldertree",
    "presentation",
]

RadarFilter = Literal["hostgroup", "servicegroup", "all_hosts", "all_services"]

PresentationTheme = Literal["midnight", "paper", "ops", "aurora"]

PresentationObjectType = Literal["host", "service", "hostgroup", "servicegroup", "aggregation"]


class ElementDisplay(TypedDict, total=False):
    mode: DisplayMode
    gadget_type: GadgetType


class ElementLabel(TypedDict, total=False):
    """A presentation element's label — unlike :class:`MapLabel` it carries no
    position of its own (the element's geometry places it)."""

    show: bool
    text: str | None
    size: int
    weight: LabelWeight


class _ElementBase(TypedDict):
    id: str
    x: float
    y: float
    w: float
    h: float
    rotation: float
    z: int
    opacity: float
    locked: bool
    hidden: bool


class TextElement(_ElementBase):
    kind: Literal["text"]
    text: str
    font_size: float
    font_weight: LabelWeight
    font_style: Literal["normal", "italic"]
    text_align: LabelAlign
    line_height: float
    letter_spacing: float


class DataElement(_ElementBase):
    kind: Literal["data"]
    object_type: PresentationObjectType
    service_description: str | None
    auto_host: bool
    only_hard_states: bool
    display: ElementDisplay
    label: ElementLabel


PresentationElement = TextElement | DataElement


class StaticView(TypedDict):
    type: Literal["static"]


class WorldmapView(TypedDict):
    type: Literal["worldmap"]
    lat: float
    lng: float
    zoom: int
    tile_saturate: NotRequired[float]


class RadarView(TypedDict):
    type: Literal["radar"]
    filter: RadarFilter
    filter_value: str
    problems_only: NotRequired[bool]


class FlowView(TypedDict):
    type: Literal["flow"]
    root: NotRequired[str]
    child_layers: NotRequired[int]
    parent_layers: NotRequired[int]


class FolderTreeView(TypedDict):
    type: Literal["foldertree"]


class PresentationView(TypedDict):
    type: Literal["presentation"]
    width: int
    height: int
    theme: PresentationTheme
    elements: list[PresentationElement]


MapView = StaticView | WorldmapView | RadarView | FlowView | FolderTreeView | PresentationView


class MapObject(TypedDict):
    """One placed object. Everything past the identity and position is
    per-type, hence not required."""

    id: str
    type: ObjectType
    x: int
    y: int
    x2: NotRequired[int]
    y2: NotRequired[int]
    mid_x: NotRequired[int]
    mid_y: NotRequired[int]
    z: NotRequired[int]
    label: NotRequired[MapLabel]
    display: NotRequired[MapDisplay]
    label_border: NotRequired[str]
    # Per-object connection; absent inherits the map's. NagVis' per-object
    # ``backend_id``: the daemon batches its state fetch per connection, so one
    # map can mix monitoring sources (two Checkmk sites, ...).
    connection_id: NotRequired[str | None]
    host_name: NotRequired[str | None]
    service_description: NotRequired[str | None]
    group_name: NotRequired[str | None]
    map_name: NotRequired[str | None]
    aggregation_id: NotRequired[str | None]
    object_types: NotRequired[Literal["host", "service"]]
    object_filter: NotRequired[str | None]
    only_hard_states: NotRequired[bool]
    recognize_services: NotRequired[bool]
    image_src: NotRequired[str | None]
    line_style: NotRequired[LineStyle]
    line_width: NotRequired[int]
    line_color_border: NotRequired[str]
    line_perfdata_label: NotRequired[LinePerfdataLabel]
    line_weather_color: NotRequired[bool]
    weathermap_metric: NotRequired[str]
    weathermap_metric_out: NotRequired[str]
    textbox_background: NotRequired[str]
    textbox_border: NotRequired[str]
    textbox_width: NotRequired[int]
    textbox_height: NotRequired[int]
    graph_url: NotRequired[str | None]
    graph_embed_type: NotRequired[Literal["img", "iframe"]]
    graph_width: NotRequired[int]
    graph_height: NotRequired[int]
    url: NotRequired[str]
    url_target: NotRequired[str]


class MapPayload(TypedDict):
    name: str
    alias: str
    readonly: bool
    connection_id: str
    icon_size: int | None
    rotation_interval: int
    sort_order: int
    click_action: ClickAction
    render_mode: RenderMode
    default_z: int
    view: MapView
    objects: list[MapObject]
    hover_template: NotRequired[str | None]
    context_template: NotRequired[str | None]
    background_image: NotRequired[str | None]
    background_color: NotRequired[str]
    show_in_lists: NotRequired[bool]
    version: NotRequired[int]
