#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""REST-API ``@api_model`` mirror of the Maps map configuration.

Typed, code-generation-facing representation of a map's payload. The frontend
TypeScript types are generated from the REST OpenAPI spec instead of being
hand-maintained.

Grouping follows the Checkmk REST convention (``host_config``/``user_config``/
``site_management``): the API model groups related fields into nested
sub-``@api_model`` objects (``position``, ``binding``, ``line``, ``graph``, …),
while the *stored* map spec the daemon validates stays flat. The two shapes are
bridged by ``cmk.maps.rest_api.utils`` (``map_from_spec``/``spec_from_map``) — the
``from_internal``/``to_internal`` equivalent, applied at the endpoint boundary. The
daemon's pydantic ``cmk.maps.backend.schemas.map.MapConfig`` remains the single
source of shape *validation*; a contract test pins this mirror against it through
those mappers.

Field optionality mirrors what the SPA treats as always-present: structural
fields (a view/element discriminator, geometry the renderer always reads, the
required ``position``/``link`` groups, ``view``/``objects``) are *required* (no
default); genuinely optional groups and fields are *omittable* (``| ApiOmitted``,
defaulting to ``ApiOmitted``). Per the framework, required fields carry no default
and must precede the omittable ones in every model.

Every model class is prefixed with ``Map`` so the generated OpenAPI component /
TypeScript type names stay unambiguous in the shared spec namespace.
"""

from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.maps.shared.filters import normalize_object_filter
from cmk.maps.shared.map_payload import (
    ClickAction,
    LinePerfdataLabel,
    LineStyle,
    ObjectType,
    PresentationObjectType,
    PresentationTheme,
    RenderMode,
)
from cmk.maps.shared.validators import validate_color

# Reject CSS-injection payloads in user-supplied colors at the REST write
# boundary (defense in depth — the SPA also escapes these at the render sink).
# Applied to every color field the daemon's ``cmk.maps.backend.schemas.map`` /
# ``.schemas.presentation`` also validate, so the REST mirror is never laxer than the
# daemon. ``validate_color`` passes ``None``/``""`` through, so it composes with the
# optional/nullable fields below.
_Color = Annotated[str, AfterValidator(validate_color)]


def _normalize_object_filter(value: str) -> str | None:
    # Mirror the daemon's ``map.py`` field validator so the REST write path is
    # never laxer than the daemon: an empty filter means "no filter", anything
    # else must be safe ``Filter:`` combinator lines. Without this the store
    # would persist a filter the daemon later rejects, leaving the map offline.
    if not value.strip():
        return None
    return normalize_object_filter(value)


# ``normalize_object_filter`` raises on non-``Filter:`` input, so a bad filter is a
# 422 at the REST boundary instead of a silently-stored value that bricks the map.
_ObjectFilter = Annotated[str, AfterValidator(_normalize_object_filter)]


# --------------------------------------------------------------------------- #
# Presentation-slide elements                                                 #
# --------------------------------------------------------------------------- #


@api_model
class MapElementTransform:
    """Shared geometry block for every presentation element (the daemon's
    ``_ElementBase``): position, size, rotation, stacking and editor flags."""

    x: float = api_field(description="Absolute slide x in pixels.", example=100.0)
    y: float = api_field(description="Absolute slide y in pixels.", example=200.0)
    w: float = api_field(description="Width in pixels.", example=120.0)
    h: float = api_field(description="Height in pixels.", example=80.0)
    rotation: float = api_field(description="Rotation in degrees.", example=0.0)
    z: int = api_field(description="Stacking order.", example=0)
    opacity: float = api_field(description="Opacity 0..1.", example=1.0)
    locked: bool = api_field(
        description="Whether the element is locked in the editor.", example=False
    )
    hidden: bool = api_field(description="Whether the element is hidden.", example=False)


@api_model
class MapElementDisplay:
    mode: Literal["icon", "text", "gadget"] = api_field(
        description="Render mode for the data element.", example="icon"
    )
    image: str | None | ApiOmitted = api_field(
        description="Icon image name.", example="icon_server", default_factory=ApiOmitted
    )
    image_size: int | None | ApiOmitted = api_field(
        description="Icon size in pixels.", example=32, default_factory=ApiOmitted
    )
    gadget_type: Literal["gauge", "bar", "trafficlight", "value"] | None | ApiOmitted = api_field(
        description="Gadget kind when mode is 'gadget'.",
        example="gauge",
        default_factory=ApiOmitted,
    )
    gadget_metric: str | None | ApiOmitted = api_field(
        description="Metric name for the gadget.", example="load1", default_factory=ApiOmitted
    )


@api_model
class MapElementLabel:
    show: bool = api_field(description="Whether the element label is rendered.", example=True)
    size: int = api_field(description="Font size in pixels.", example=12)
    text: str | None | ApiOmitted = api_field(
        description="Explicit label text.", example="web-01", default_factory=ApiOmitted
    )
    color: _Color | None | ApiOmitted = api_field(
        description="Text color; null inherits the theme.",
        example="#ffffff",
        default_factory=ApiOmitted,
    )
    background: _Color | None | ApiOmitted = api_field(
        description="Background color.", example="transparent", default_factory=ApiOmitted
    )
    weight: Literal["normal", "bold"] | None | ApiOmitted = api_field(
        description="Font weight.", example="bold", default_factory=ApiOmitted
    )
    align: Literal["left", "right", "center"] | None | ApiOmitted = api_field(
        description="Text alignment.", example="center", default_factory=ApiOmitted
    )


@api_model
class MapShapeElement:
    kind: Literal["shape"] = api_field(description="Element discriminator.", example="shape")
    id: str = api_field(description="Client-generated unique element id.", example="elem-1")
    transform: MapElementTransform = api_field(description="Geometry and editor state.")
    shape: Literal["rect", "ellipse", "line", "arrow"] = api_field(
        description="Shape kind.", example="rect"
    )
    stroke_width: float = api_field(description="Stroke width in pixels.", example=1.0)
    corner_radius: float = api_field(description="Corner radius in pixels.", example=4.0)
    dash: Literal["solid", "dashed", "dotted"] = api_field(
        description="Stroke dash style.", example="solid"
    )
    name: str | None | ApiOmitted = api_field(
        description="Editor display name.", example="Frame", default_factory=ApiOmitted
    )
    fill: _Color | None | ApiOmitted = api_field(
        description="Fill color.", example="#3b82f6", default_factory=ApiOmitted
    )
    stroke: _Color | None | ApiOmitted = api_field(
        description="Stroke color.", example="#1e3a8a", default_factory=ApiOmitted
    )
    connection_id: str | None | ApiOmitted = api_field(
        description="Monitoring connection override.", example="live_1", default_factory=ApiOmitted
    )
    object_type: PresentationObjectType | None | ApiOmitted = api_field(
        description="Bound monitoring object type.", example="host", default_factory=ApiOmitted
    )
    host_name: str | None | ApiOmitted = api_field(
        description="Bound host name.", example="web-01", default_factory=ApiOmitted
    )
    service_description: str | None | ApiOmitted = api_field(
        description="Bound service.", example="CPU load", default_factory=ApiOmitted
    )
    group_name: str | None | ApiOmitted = api_field(
        description="Bound group name.", example="linux", default_factory=ApiOmitted
    )
    aggregation_id: str | None | ApiOmitted = api_field(
        description="Bound BI aggregation id.", example="agg-1", default_factory=ApiOmitted
    )
    auto_host: bool | ApiOmitted = api_field(
        description="Resolve the connection's primary host.",
        example=False,
        default_factory=ApiOmitted,
    )
    only_hard_states: bool | ApiOmitted = api_field(
        description="Use last hard states.", example=False, default_factory=ApiOmitted
    )
    label: MapElementLabel | None | ApiOmitted = api_field(
        description="State label config.",
        example={"show": True, "size": 12},
        default_factory=ApiOmitted,
    )
    start_ref: str | None | ApiOmitted = api_field(
        description="Start docking element id.", example="elem-2", default_factory=ApiOmitted
    )
    end_ref: str | None | ApiOmitted = api_field(
        description="End docking element id.", example="elem-3", default_factory=ApiOmitted
    )
    flow: bool | ApiOmitted = api_field(
        description="Animate as a weathermap connector.",
        example=False,
        default_factory=ApiOmitted,
    )
    flow_metric: str | None | ApiOmitted = api_field(
        description="Forward-flow metric.", example="if_in_octets", default_factory=ApiOmitted
    )
    flow_metric_back: str | None | ApiOmitted = api_field(
        description="Return-flow metric.", example="if_out_octets", default_factory=ApiOmitted
    )
    data_slot: bool | ApiOmitted = api_field(
        description="Marks an intended data slot placeholder.",
        example=False,
        default_factory=ApiOmitted,
    )


@api_model
class MapTextElement:
    kind: Literal["text"] = api_field(description="Element discriminator.", example="text")
    id: str = api_field(description="Client-generated unique element id.", example="elem-1")
    transform: MapElementTransform = api_field(description="Geometry and editor state.")
    text: str = api_field(description="Text content.", example="Datacenter Munich")
    font_size: float = api_field(description="Font size in pixels.", example=24.0)
    font_weight: Literal["normal", "bold"] = api_field(description="Font weight.", example="bold")
    font_style: Literal["normal", "italic"] = api_field(description="Font style.", example="normal")
    text_align: Literal["left", "center", "right", "justify"] = api_field(
        description="Text alignment.", example="center"
    )
    line_height: float = api_field(description="Line height factor.", example=1.3)
    letter_spacing: float = api_field(description="Letter spacing in pixels.", example=0.0)
    name: str | None | ApiOmitted = api_field(
        description="Editor display name.", example="Title", default_factory=ApiOmitted
    )
    font_family: str | None | ApiOmitted = api_field(
        description="Font family.", example="Inter", default_factory=ApiOmitted
    )
    color: _Color | None | ApiOmitted = api_field(
        description="Text color; null inherits theme.",
        example="#ffffff",
        default_factory=ApiOmitted,
    )
    background: _Color | None | ApiOmitted = api_field(
        description="Background color.", example="transparent", default_factory=ApiOmitted
    )


@api_model
class MapImageElement:
    kind: Literal["image"] = api_field(description="Element discriminator.", example="image")
    id: str = api_field(description="Client-generated unique element id.", example="elem-1")
    transform: MapElementTransform = api_field(description="Geometry and editor state.")
    fit: Literal["cover", "contain", "fill"] = api_field(
        description="Object fit.", example="contain"
    )
    name: str | None | ApiOmitted = api_field(
        description="Editor display name.", example="Logo", default_factory=ApiOmitted
    )
    src: str | None | ApiOmitted = api_field(
        description="Image source (store filename or URL).",
        example="/logo.png",
        default_factory=ApiOmitted,
    )
    alt: str | None | ApiOmitted = api_field(
        description="Alt text.", example="Company logo", default_factory=ApiOmitted
    )


@api_model
class MapDataElement:
    kind: Literal["data"] = api_field(description="Element discriminator.", example="data")
    id: str = api_field(description="Client-generated unique element id.", example="elem-1")
    transform: MapElementTransform = api_field(description="Geometry and editor state.")
    only_hard_states: bool = api_field(description="Use last hard states.", example=False)
    display: MapElementDisplay = api_field(
        description="Render mode config.", example={"mode": "icon"}
    )
    name: str | None | ApiOmitted = api_field(
        description="Editor display name.", example="web-01", default_factory=ApiOmitted
    )
    connection_id: str | None | ApiOmitted = api_field(
        description="Monitoring connection override.", example="live_1", default_factory=ApiOmitted
    )
    object_type: PresentationObjectType | None | ApiOmitted = api_field(
        description="Bound monitoring object type.", example="host", default_factory=ApiOmitted
    )
    host_name: str | None | ApiOmitted = api_field(
        description="Bound host name.", example="web-01", default_factory=ApiOmitted
    )
    service_description: str | None | ApiOmitted = api_field(
        description="Bound service.", example="CPU load", default_factory=ApiOmitted
    )
    group_name: str | None | ApiOmitted = api_field(
        description="Bound group name.", example="linux", default_factory=ApiOmitted
    )
    aggregation_id: str | None | ApiOmitted = api_field(
        description="Bound BI aggregation id.", example="agg-1", default_factory=ApiOmitted
    )
    auto_host: bool | ApiOmitted = api_field(
        description="Auto-bind to the connection's primary host.",
        example=False,
        default_factory=ApiOmitted,
    )
    label: MapElementLabel | None | ApiOmitted = api_field(
        description="Label config.", example={"show": True, "size": 12}, default_factory=ApiOmitted
    )
    fill: _Color | None | ApiOmitted = api_field(
        description="Fill color.", example="#3b82f6", default_factory=ApiOmitted
    )
    stroke: _Color | None | ApiOmitted = api_field(
        description="Stroke color.", example="#1e3a8a", default_factory=ApiOmitted
    )


@api_model
class MapGroupElement:
    kind: Literal["group"] = api_field(description="Element discriminator.", example="group")
    id: str = api_field(description="Client-generated unique element id.", example="elem-1")
    transform: MapElementTransform = api_field(description="Geometry and editor state.")
    children: list[str] = api_field(
        description="Element ids grouped under this group.", example=["elem-2", "elem-3"]
    )
    name: str | None | ApiOmitted = api_field(
        description="Editor display name.", example="Rack A", default_factory=ApiOmitted
    )


MapPresentationElement = Annotated[
    MapShapeElement | MapTextElement | MapImageElement | MapDataElement | MapGroupElement,
    Field(discriminator="kind"),
]


# --------------------------------------------------------------------------- #
# Map views                                                                   #
# --------------------------------------------------------------------------- #


@api_model
class MapStaticView:
    type: Literal["static"] = api_field(description="View discriminator.", example="static")
    problems_only: bool | ApiOmitted = api_field(
        description="Show only objects with problems.", example=False, default_factory=ApiOmitted
    )


@api_model
class MapWorldmapView:
    type: Literal["worldmap"] = api_field(description="View discriminator.", example="worldmap")
    lat: float = api_field(description="Initial map center latitude.", example=51.0)
    lng: float = api_field(description="Initial map center longitude.", example=10.0)
    zoom: int = api_field(description="Initial zoom level.", example=5)
    tile_url: str | None | ApiOmitted = api_field(
        description="Leaflet tile URL template override.",
        example="https://tiles.example.com/{z}/{x}/{y}.png",
        default_factory=ApiOmitted,
    )
    tile_saturate: float | None | ApiOmitted = api_field(
        description="CSS saturate() percent (0..100).", example=100.0, default_factory=ApiOmitted
    )
    auto_source: Literal["all_hosts", "hostgroup", "servicegroup"] | None | ApiOmitted = api_field(
        description="Automap source that populates geo-tagged hosts.",
        example="all_hosts",
        default_factory=ApiOmitted,
    )
    auto_filter_value: str | ApiOmitted = api_field(
        description="Automap group filter value.", example="linux", default_factory=ApiOmitted
    )
    problems_only: bool | ApiOmitted = api_field(
        description="Show only objects with problems.", example=False, default_factory=ApiOmitted
    )


@api_model
class MapRadarView:
    type: Literal["radar"] = api_field(description="View discriminator.", example="radar")
    filter: Literal["hostgroup", "servicegroup", "all_hosts", "all_services"] = api_field(
        description="Radar membership source.", example="hostgroup"
    )
    filter_value: str = api_field(description="Group filter value.", example="linux")
    problems_only: bool | ApiOmitted = api_field(
        description="Show only objects with problems.", example=False, default_factory=ApiOmitted
    )


@api_model
class MapFlowNodePosition:
    x: float = api_field(description="Pinned node x position.", example=120.0)
    y: float = api_field(description="Pinned node y position.", example=80.0)


@api_model
class MapFlowView:
    type: Literal["flow"] = api_field(description="View discriminator.", example="flow")
    root: str | None | ApiOmitted = api_field(
        description="Root host for the flow graph.",
        example="core-router",
        default_factory=ApiOmitted,
    )
    child_layers: int | None | ApiOmitted = api_field(
        description="Downward layer limit (-1 = all).", example=2, default_factory=ApiOmitted
    )
    parent_layers: int | None | ApiOmitted = api_field(
        description="Upward layer limit (-1 = all).", example=1, default_factory=ApiOmitted
    )
    top_affected_hosts: int | None | ApiOmitted = api_field(
        description="Per-map override of the top-affected-hosts limit.",
        example=10,
        default_factory=ApiOmitted,
    )
    max_services_per_host: int | None | ApiOmitted = api_field(
        description="Per-map override of the services-per-host limit.",
        example=5,
        default_factory=ApiOmitted,
    )
    positions: dict[str, MapFlowNodePosition] | ApiOmitted = api_field(
        description="Pinned host positions from operator drags.",
        example={"web-01": {"x": 120.0, "y": 80.0}},
        default_factory=ApiOmitted,
    )
    service_layout: Literal["off", "donut", "fan", "orbit", "row"] | None | ApiOmitted = api_field(
        description="Service-node layout.", example="donut", default_factory=ApiOmitted
    )
    problems_only: bool | ApiOmitted = api_field(
        description="Show only objects with problems.", example=False, default_factory=ApiOmitted
    )


@api_model
class MapFolderTreeView:
    type: Literal["foldertree"] = api_field(description="View discriminator.", example="foldertree")
    root_folder: str | ApiOmitted = api_field(
        description="WATO folder id or path slug ('' = root).",
        example="",
        default_factory=ApiOmitted,
    )
    default_view: Literal["list", "map"] | ApiOmitted = api_field(
        description="Presentation the map opens in.", example="map", default_factory=ApiOmitted
    )
    default_expand_depth: int | ApiOmitted = api_field(
        description="Initial expand depth.", example=2, default_factory=ApiOmitted
    )
    show_services: bool | ApiOmitted = api_field(
        description="Include services in the tree.", example=True, default_factory=ApiOmitted
    )
    show_empty_folders: bool | ApiOmitted = api_field(
        description="Show folders without hosts.", example=False, default_factory=ApiOmitted
    )
    problems_only: bool | ApiOmitted = api_field(
        description="Show only objects with problems.", example=False, default_factory=ApiOmitted
    )
    problems_severity: Literal["any", "critical"] | ApiOmitted = api_field(
        description="What counts as a problem for the filter.",
        example="any",
        default_factory=ApiOmitted,
    )
    only_hard_states: bool | ApiOmitted = api_field(
        description="Use last hard states.", example=False, default_factory=ApiOmitted
    )
    sites: list[str] | ApiOmitted = api_field(
        description="Scope to these site ids ([] = all).",
        example=["central"],
        default_factory=ApiOmitted,
    )


@api_model
class MapPresentationView:
    type: Literal["presentation"] = api_field(
        description="View discriminator.", example="presentation"
    )
    width: int = api_field(description="Slide stage width in pixels.", example=1920)
    height: int = api_field(description="Slide stage height in pixels.", example=1080)
    theme: PresentationTheme = api_field(description="Slide theme.", example="midnight")
    elements: list[MapPresentationElement] = api_field(
        description="Design elements on the slide.",
        example=[{"kind": "text", "id": "t1", "transform": {}, "text": "Title", "font_size": 24}],
    )
    background: _Color | None | ApiOmitted = api_field(
        description="Background color.", example="#0f172a", default_factory=ApiOmitted
    )
    background_image: str | None | ApiOmitted = api_field(
        description="Background image source.", example="/floorplan.png", default_factory=ApiOmitted
    )
    problems_only: bool | ApiOmitted = api_field(
        description="Show only objects with problems.", example=False, default_factory=ApiOmitted
    )


MapView = Annotated[
    MapStaticView
    | MapWorldmapView
    | MapRadarView
    | MapFlowView
    | MapFolderTreeView
    | MapPresentationView,
    Field(discriminator="type"),
]


# --------------------------------------------------------------------------- #
# Map objects (grouped)                                                       #
# --------------------------------------------------------------------------- #


@api_model
class MapObjectPosition:
    """Where the object sits on the map (canvas x/y for static/flow/radar maps,
    lat/lng for worldmaps)."""

    x: int | float = api_field(description="Canvas x position.", example=100)
    y: int | float = api_field(description="Canvas y position.", example=200)
    z: int | None | ApiOmitted = api_field(
        description="Stacking order; null inherits the map's default_z.",
        example=1,
        default_factory=ApiOmitted,
    )
    lat: float | None | ApiOmitted = api_field(
        description="Latitude (worldmap).", example=48.1, default_factory=ApiOmitted
    )
    lng: float | None | ApiOmitted = api_field(
        description="Longitude (worldmap).", example=11.6, default_factory=ApiOmitted
    )


@api_model
class MapObjectBinding:
    """What monitoring entity the object is bound to."""

    connection_id: str | None | ApiOmitted = api_field(
        description="Per-object connection override; null inherits the map's.",
        example="live_1",
        default_factory=ApiOmitted,
    )
    host_name: str | None | ApiOmitted = api_field(
        description="Bound host name.", example="web-01", default_factory=ApiOmitted
    )
    service_description: str | None | ApiOmitted = api_field(
        description="Bound service.", example="CPU load", default_factory=ApiOmitted
    )
    group_name: str | None | ApiOmitted = api_field(
        description="Bound group name.", example="linux", default_factory=ApiOmitted
    )
    map_name: str | None | ApiOmitted = api_field(
        description="Linked map name.", example="datacenter-muc", default_factory=ApiOmitted
    )
    aggregation_id: str | None | ApiOmitted = api_field(
        description="Bound BI aggregation id.", example="agg-1", default_factory=ApiOmitted
    )
    object_types: Literal["host", "service"] | None | ApiOmitted = api_field(
        description="Dyngroup object type.", example="host", default_factory=ApiOmitted
    )
    object_filter: _ObjectFilter | None | ApiOmitted = api_field(
        description="Dyngroup Livestatus filter.",
        example="Filter: host_name ~ web\n",
        default_factory=ApiOmitted,
    )
    only_hard_states: bool | ApiOmitted = api_field(
        description="Use last hard states.", example=False, default_factory=ApiOmitted
    )
    recognize_services: bool | ApiOmitted = api_field(
        description="Fold service states into the object.",
        example=True,
        default_factory=ApiOmitted,
    )
    expand_depth: int | ApiOmitted = api_field(
        description="Map-link/aggregation expand depth (0..10).",
        example=1,
        default_factory=ApiOmitted,
    )


@api_model
class MapObjectCmkLabel:
    """Checkmk-label filter for a cmk_label object."""

    name: str | None | ApiOmitted = api_field(
        description="Checkmk label key filter.", example="cmk/os_family", default_factory=ApiOmitted
    )
    value: str | None | ApiOmitted = api_field(
        description="Checkmk label value filter.", example="linux", default_factory=ApiOmitted
    )
    target: Literal["hosts", "services"] | None | ApiOmitted = api_field(
        description="Label target objects.", example="hosts", default_factory=ApiOmitted
    )


@api_model
class MapObjectBundle:
    """Geo-bundle grouping for worldmap objects."""

    kind: Literal["static", "location"] | None | ApiOmitted = api_field(
        description="Geo bundle kind.", example="location", default_factory=ApiOmitted
    )
    hosts: list[str] | None | ApiOmitted = api_field(
        description="Bundle member hosts.", example=["web-01", "web-02"], default_factory=ApiOmitted
    )
    precision: int | None | ApiOmitted = api_field(
        description="Geo bundle coordinate precision.", example=3, default_factory=ApiOmitted
    )


@api_model
class MapObjectLine:
    """Geometry and styling for a line/connection object."""

    x2: int | float | None | ApiOmitted = api_field(
        description="Line end x.", example=300, default_factory=ApiOmitted
    )
    y2: int | float | None | ApiOmitted = api_field(
        description="Line end y.", example=400, default_factory=ApiOmitted
    )
    lat2: float | None | ApiOmitted = api_field(
        description="Line end latitude.", example=48.2, default_factory=ApiOmitted
    )
    lng2: float | None | ApiOmitted = api_field(
        description="Line end longitude.", example=11.7, default_factory=ApiOmitted
    )
    mid_x: int | float | None | ApiOmitted = api_field(
        description="Line bend point x.", example=200, default_factory=ApiOmitted
    )
    mid_y: int | float | None | ApiOmitted = api_field(
        description="Line bend point y.", example=300, default_factory=ApiOmitted
    )
    start_ref: str | None | ApiOmitted = api_field(
        description="Start docking object id.", example="o2", default_factory=ApiOmitted
    )
    end_ref: str | None | ApiOmitted = api_field(
        description="End docking object id.", example="o3", default_factory=ApiOmitted
    )
    style: LineStyle | None | ApiOmitted = api_field(
        description="Line style.", example="arrow_end", default_factory=ApiOmitted
    )
    width: int | None | ApiOmitted = api_field(
        description="Line stroke width (px).", example=2, default_factory=ApiOmitted
    )
    perfdata_label: LinePerfdataLabel | ApiOmitted = api_field(
        description="Perfdata label at the line midpoint.",
        example="bandwidth",
        default_factory=ApiOmitted,
    )
    weather_color: bool | ApiOmitted = api_field(
        description="Color the line by utilization.", example=True, default_factory=ApiOmitted
    )
    metric_in: str | None | ApiOmitted = api_field(
        description="Inbound weathermap metric.",
        example="if_in_octets",
        default_factory=ApiOmitted,
    )
    metric_out: str | None | ApiOmitted = api_field(
        description="Outbound weathermap metric.",
        example="if_out_octets",
        default_factory=ApiOmitted,
    )
    color: _Color | None | ApiOmitted = api_field(
        description="Line color.", example="#3b82f6", default_factory=ApiOmitted
    )
    color_border: _Color | None | ApiOmitted = api_field(
        description="Line border color.", example="#1e3a8a", default_factory=ApiOmitted
    )


@api_model
class MapObjectTextbox:
    """Styling for a textbox object."""

    background: _Color | None | ApiOmitted = api_field(
        description="Textbox background color.", example="#ffffff", default_factory=ApiOmitted
    )
    border: _Color | None | ApiOmitted = api_field(
        description="Textbox border color.", example="#cccccc", default_factory=ApiOmitted
    )
    width: int | None | ApiOmitted = api_field(
        description="Textbox width in pixels.", example=120, default_factory=ApiOmitted
    )
    height: int | None | ApiOmitted = api_field(
        description="Textbox height in pixels.", example=60, default_factory=ApiOmitted
    )


@api_model
class MapObjectGraph:
    """Embedded-graph configuration for a graph object."""

    url: str | None | ApiOmitted = api_field(
        description="Embedded graph URL.",
        example="/check_mk/graph.py?host=web-01",
        default_factory=ApiOmitted,
    )
    embed_type: Literal["img", "iframe"] | ApiOmitted = api_field(
        description="Graph embed mode.", example="img", default_factory=ApiOmitted
    )
    width: int | ApiOmitted = api_field(
        description="Graph width in pixels.", example=400, default_factory=ApiOmitted
    )
    height: int | ApiOmitted = api_field(
        description="Graph height in pixels.", example=200, default_factory=ApiOmitted
    )
    refresh_interval: int | ApiOmitted = api_field(
        description="Graph refresh interval (s).", example=60, default_factory=ApiOmitted
    )
    metric: list[str] | None | ApiOmitted = api_field(
        description="Graph metric names.", example=["load1"], default_factory=ApiOmitted
    )
    id: str | None | ApiOmitted = api_field(
        description="Graph template id.", example="cpu_load", default_factory=ApiOmitted
    )
    time_window: int | None | ApiOmitted = api_field(
        description="Graph time window (minutes).", example=240, default_factory=ApiOmitted
    )


@api_model
class MapObjectFilter:
    """Member exclusion for aggregating objects (host/group/map)."""

    exclude_members: str | None | ApiOmitted = api_field(
        description="Member exclusion filter.", example="test-*", default_factory=ApiOmitted
    )
    exclude_member_states: str | None | ApiOmitted = api_field(
        description="Member-state exclusion.", example="ok", default_factory=ApiOmitted
    )


@api_model
class MapObjectLink:
    """Click-through and hover behaviour for the object."""

    url_target: str = api_field(
        description="Link target for the object's click-through URL.", example="_blank"
    )
    url: str | None | ApiOmitted = api_field(
        description="Click-through URL.",
        example="/check_mk/view.py?host=web-01",
        default_factory=ApiOmitted,
    )
    hover_url: str | None | ApiOmitted = api_field(
        description="Hover preview URL.",
        example="/check_mk/hover.py?host=web-01",
        default_factory=ApiOmitted,
    )
    hover_template: str | None | ApiOmitted = api_field(
        description="Hover template.", example="{{ host_name }}", default_factory=ApiOmitted
    )
    context_template: str | None | ApiOmitted = api_field(
        description="Context-menu template.", example="{{ host_name }}", default_factory=ApiOmitted
    )


@api_model
class MapObjectLabel:
    """The object's name label (position, styling, truncation)."""

    show: bool = api_field(description="Whether the label is rendered.", example=True)
    x: int = api_field(description="Label x offset in pixels.", example=0)
    y: int = api_field(description="Label y offset in pixels.", example=12)
    size: int = api_field(description="Font size in pixels.", example=12)
    color: _Color = api_field(description="Text color (hex/named/transparent).", example="#ffffff")
    background: _Color = api_field(description="Background color.", example="transparent")
    text: str | None | ApiOmitted = api_field(
        description="Explicit label text; null derives it.",
        example="web-01",
        default_factory=ApiOmitted,
    )
    width: int | None | ApiOmitted = api_field(
        description="Fixed pixel width that wraps text.",
        example=120,
        default_factory=ApiOmitted,
    )
    weight: Literal["normal", "bold"] | None | ApiOmitted = api_field(
        description="Font weight.", example="bold", default_factory=ApiOmitted
    )
    align: Literal["left", "right", "center", "justify"] | None | ApiOmitted = api_field(
        description="Text alignment.", example="center", default_factory=ApiOmitted
    )
    border: _Color | None | ApiOmitted = api_field(
        description="Label border color.", example="#1e3a8a", default_factory=ApiOmitted
    )
    max_length: int | None | ApiOmitted = api_field(
        description="Label truncation length.", example=20, default_factory=ApiOmitted
    )


@api_model
class MapObjectDisplay:
    """How the object renders (icon/text/gadget) and its custom icon."""

    mode: Literal["icon", "text", "gadget"] = api_field(
        description="Render mode for the object.", example="icon"
    )
    image: str | None | ApiOmitted = api_field(
        description="Custom icon image name.", example="icon_server", default_factory=ApiOmitted
    )
    image_size: int | None | ApiOmitted = api_field(
        description="Icon size in pixels.", example=32, default_factory=ApiOmitted
    )
    gadget_type: Literal["gauge", "bar", "trafficlight", "value"] | None | ApiOmitted = api_field(
        description="Gadget kind when mode is 'gadget'.",
        example="gauge",
        default_factory=ApiOmitted,
    )
    gadget_metric: str | None | ApiOmitted = api_field(
        description="Metric name for the gadget.", example="load1", default_factory=ApiOmitted
    )


@api_model
class MapElement:
    """A placed map object. Structural identity (``id``/``type``), the required
    ``position`` and ``link`` groups, then per-concern optional groups — only the
    ones relevant to the object's ``type`` are populated."""

    id: str = api_field(description="Unique object id within the map.", example="o1")
    type: ObjectType = api_field(description="Object type.", example="host")
    position: MapObjectPosition = api_field(description="Where the object sits on the map.")
    link: MapObjectLink = api_field(description="Click-through and hover behaviour.")
    image_src: str | None | ApiOmitted = api_field(
        description="Image source (image objects).", example="/logo.png", default_factory=ApiOmitted
    )
    binding: MapObjectBinding | ApiOmitted = api_field(
        description="Bound monitoring entity.", default_factory=ApiOmitted
    )
    cmk_label: MapObjectCmkLabel | ApiOmitted = api_field(
        description="Checkmk-label filter (cmk_label objects).", default_factory=ApiOmitted
    )
    bundle: MapObjectBundle | ApiOmitted = api_field(
        description="Geo-bundle grouping (worldmap).", default_factory=ApiOmitted
    )
    line: MapObjectLine | ApiOmitted = api_field(
        description="Line geometry and styling (line objects).", default_factory=ApiOmitted
    )
    textbox: MapObjectTextbox | ApiOmitted = api_field(
        description="Textbox styling (textbox objects).", default_factory=ApiOmitted
    )
    graph: MapObjectGraph | ApiOmitted = api_field(
        description="Embedded-graph config (graph objects).", default_factory=ApiOmitted
    )
    filter: MapObjectFilter | ApiOmitted = api_field(
        description="Member exclusion (aggregating objects).", default_factory=ApiOmitted
    )
    label: MapObjectLabel | ApiOmitted = api_field(
        description="Object name label.", default_factory=ApiOmitted
    )
    display: MapObjectDisplay | ApiOmitted = api_field(
        description="Render mode and custom icon.", default_factory=ApiOmitted
    )


@api_model
class MapConfig:
    """Full map payload — the create/update request body and show response."""

    name: str = api_field(
        description="Unique map name (URL/permission id).", example="datacenter-muc"
    )
    alias: str = api_field(description="Human-readable title.", example="Datacenter Munich")
    connection_id: str = api_field(description="Default monitoring connection.", example="live_1")
    icon_size: int | None = api_field(
        description="Default icon size in pixels (null = default).", example=32
    )
    rotation_interval: int = api_field(description="Auto-rotation interval (s).", example=0)
    sort_order: int = api_field(description="Sort order in listings.", example=0)
    click_action: ClickAction = api_field(
        description="Default object click action.", example="link"
    )
    view: MapView = api_field(
        description="Map view (renderer + geometry).", example={"type": "static"}
    )
    objects: list[MapElement] = api_field(
        description="Placed objects (static/flow/worldmap/radar maps).",
        example=[
            {
                "id": "o1",
                "type": "host",
                "position": {"x": 100, "y": 200},
                "link": {"url_target": "_blank"},
                "binding": {"host_name": "web-01"},
            }
        ],
    )
    hover_template: str | None | ApiOmitted = api_field(
        description="Map-wide hover template.",
        example="{{ host_name }}",
        default_factory=ApiOmitted,
    )
    context_template: str | None | ApiOmitted = api_field(
        description="Map-wide context template.",
        example="{{ host_name }}",
        default_factory=ApiOmitted,
    )
    background_image: str | None | ApiOmitted = api_field(
        description="Background image source.", example="/floorplan.png", default_factory=ApiOmitted
    )
    background_color: str | None | ApiOmitted = api_field(
        description="Background color.", example="#0f172a", default_factory=ApiOmitted
    )
    render_mode: RenderMode | ApiOmitted = api_field(
        description="Rendering mode.", example="default", default_factory=ApiOmitted
    )
    default_z: int | ApiOmitted = api_field(
        description="Map-wide default stacking order.", example=1, default_factory=ApiOmitted
    )
    version: int | ApiOmitted = api_field(
        description="Monotonic version for optimistic locking.",
        example=1,
        default_factory=ApiOmitted,
    )
    canvas_width: int | None | ApiOmitted = api_field(
        description="Persisted canvas width.", example=1920, default_factory=ApiOmitted
    )
    canvas_height: int | None | ApiOmitted = api_field(
        description="Persisted canvas height.", example=1080, default_factory=ApiOmitted
    )


@api_model
class MapListEntry:
    """Light list projection — drops the heavy ``objects`` list.

    Carries the map-level display fields the SPA list needs (the card
    thumbnails read ``view``, the settings modal edits ``click_action`` and the
    templates), matching ``cmk.maps.gui.store.map_to_read`` so the runtime
    list endpoint and the page-hydrated home view agree on one row shape. The
    map-level fields are already flat and few, so this projection is not grouped.
    """

    name: str = api_field(description="Unique map name.", example="datacenter-muc")
    alias: str = api_field(description="Human-readable title.", example="Datacenter Munich")
    connection_id: str = api_field(description="Default monitoring connection.", example="live_1")
    view_type: str = api_field(
        description="Renderer type (static/flow/worldmap/...).", example="static"
    )
    view: MapView = api_field(
        description="Map view (renderer + geometry).", example={"type": "static"}
    )
    click_action: ClickAction = api_field(
        description="Default object click action.", example="link"
    )
    object_count: int = api_field(description="Number of placed objects/elements.", example=12)
    background_image: str | None | ApiOmitted = api_field(
        description="Background image source.", example="/floorplan.png", default_factory=ApiOmitted
    )
    background_color: str | None | ApiOmitted = api_field(
        description="Background color.", example="#0f172a", default_factory=ApiOmitted
    )
    icon_size: int | None | ApiOmitted = api_field(
        description="Default icon size.", example=32, default_factory=ApiOmitted
    )
    rotation_interval: int | ApiOmitted = api_field(
        description="Auto-rotation interval (s).", example=0, default_factory=ApiOmitted
    )
    sort_order: int | ApiOmitted = api_field(
        description="Sort order in listings.", example=0, default_factory=ApiOmitted
    )
    version: int | ApiOmitted = api_field(
        description="Map version.", example=1, default_factory=ApiOmitted
    )
    render_mode: RenderMode | ApiOmitted = api_field(
        description="Rendering mode.", example="default", default_factory=ApiOmitted
    )
    hover_template: str | None | ApiOmitted = api_field(
        description="Map-wide hover template.",
        example="{{ host_name }}",
        default_factory=ApiOmitted,
    )
    context_template: str | None | ApiOmitted = api_field(
        description="Map-wide context template.",
        example="{{ host_name }}",
        default_factory=ApiOmitted,
    )
    default_z: int | ApiOmitted = api_field(
        description="Map-wide default stacking order.", example=1, default_factory=ApiOmitted
    )
